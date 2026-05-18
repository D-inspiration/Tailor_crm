from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from services.auth_gateway import AuthGateway

PUBLIC_PATHS = getattr(settings, 'FLASK_PUBLIC_PATHS', [
    '/login/', '/logout/', '/accounts/',
    '/static/', '/media/', '/public/', '/admin/'
])


class FlaskSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # 1. Skip public routes completely
        if any(request.path.startswith(p) for p in PUBLIC_PATHS):
            return self.get_response(request)

        # 2. If Django user not authenticated, do NOT enforce Flask
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 3. Get session safely
        session_id = (
            request.headers.get("X-SESSION-ID")
            or request.session.get("flask_session_id")
        )

        # 4. SAFE DEFAULT: no session → continue request
        if not session_id:
            request.flask_verified = False
            request.flask_session_id = None
            request.auth_context = {}
            return self.get_response(request)

        # 5. Cache check (fast path)
        cache_key = f"flask_session:{session_id}"
        cached = cache.get(cache_key)

        if cached:
            request.flask_verified = True
            request.flask_session_id = session_id
            request.auth_context = cached
            return self.get_response(request)

        # 6. Validate with Flask (ONLY if session exists)
        response = AuthGateway.validate_session(session_id, request.user.id)

        print(f"[MIDDLEWARE] Flask validation: {response}")

        # 7. Reject invalid session
        if response.get("status") != "allow":
            if request.headers.get("HX-Request"):
                return JsonResponse(response, status=403)
            return redirect('login')

        # 8. Handle blocked accounts
        if response.get("risk_status") == "blocked":
            logout(request)
            request.session.flush()
            messages.error(
                request,
                "Account locked due to suspicious activity. Contact support."
            )
            return redirect('login')

        # 9. Store risk info
        request.session['flask_risk_status'] = response.get('risk_status', 'ok')
        request.session['flask_risk_score'] = response.get('risk_score', 0)
        request.session.modified = True

        # 10. Attach request context (safe)
        request.flask_verified = True
        request.flask_session_id = session_id
        request.auth_context = response

        # 11. Cache result briefly
        cache.set(cache_key, response, timeout=30)

        print(f"[MIDDLEWARE] Valid session {session_id[:20]} for user {request.user.id}")
        print("MIDDLEWARE SESSION:", request.session.session_key)

        return self.get_response(request)


