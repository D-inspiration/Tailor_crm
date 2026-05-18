from .auth_gateway import AuthGateway
from .identity import get_flask_user_id


def track_event(request, event_type, payload):
    try:
        session_id = (
            getattr(request, "flask_session_id", None)
            or request.session.get("flask_session_id")
        )

        # soft lookup — no exception
        user_id = request.session.get("flask_user_id")

        print(
            f"[TRACK_EVENT] session_id="
            f"{session_id[:20] if session_id else 'NONE'}..."
        )
        print(
            f"[TRACK_EVENT] user_id={user_id}, "
            f"event_type={event_type}"
        )
        print(f"[TRACK_EVENT] payload={payload}")

        if not session_id:
            print("[TRACK_EVENT] SOFT SKIP — no session_id")
            return None

        if not user_id:
            print("[TRACK_EVENT] SOFT SKIP — no flask_user_id")
            return None

        result = AuthGateway.send_event(
            session_id=session_id,
            user_id=user_id,
            event_type=event_type,
            payload=payload
        )

        print(f"[TRACK_EVENT] Flask response: {result}")

        # analytics should never block UX
        if result and result.get("status") == "deny":
            print(
                f"[TRACK_EVENT] SOFT FAIL: "
                f"{result.get('reason')}"
            )
            return None

        return result

    except Exception as e:
        print(f"[TRACK_EVENT] SOFT EXCEPTION: {e}")
        return None


