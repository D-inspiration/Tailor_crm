from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
from services.auth_gateway import AuthGateway

PUBLIC_PATHS = getattr(settings, 'FLASK_PUBLIC_PATHS', [
    '/login/', '/logout/', '/accounts/', 
    '/static/', '/media/', '/public/', '/admin/'
])

class FlaskSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in PUBLIC_PATHS):
            return self.get_response(request)
        
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        session_id = (
            request.headers.get("X-SESSION-ID") 
            or request.session.get("flask_session_id")
        )
        
        # CRITICAL: Use Flask's user_id, not Django's
        flask_user_id = request.session.get('flask_user_id')
        user_id = flask_user_id if flask_user_id is not None else request.user.id
        print(f"[MIDDLEWARE] Validating session {session_id[:20] if session_id else 'NONE'}... for user {user_id}")
        
        if not session_id:
            request.flask_verified = False
            request.flask_session_id = None
            request.auth_context = {}
            return self.get_response(request)
        
        cache_key = f"flask_session:{session_id}"
        cached = cache.get(cache_key)
        
        if cached:
            request.flask_verified = True
            request.flask_session_id = session_id
            request.auth_context = cached
            return self.get_response(request)
        
        response = AuthGateway.validate_session(session_id, user_id)
        print(f"[MIDDLEWARE] Flask validation: {response}")
        
        if response.get("status") != "allow":
            if request.headers.get("HX-Request"):
                return JsonResponse(response, status=403)
            from django.shortcuts import redirect
            return redirect('login')
            
            
        print(f"[MIDDLEWARE] Setting request.flask_session_id = {session_id[:20]}...")


        request.flask_verified = True
        request.flask_session_id = session_id
        request.auth_context = response
        cache.set(cache_key, response, timeout=30)
        
        return self.get_response(request)



