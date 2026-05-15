from .auth_gateway import AuthGateway

def track_event(request, event_type, payload):
    session_id = getattr(request, "flask_session_id", None) or request.session.get("flask_session_id")
    user_id = request.session.get('flask_user_id')
    if user_id is None:
        user_id = request.user.id
    

    print(f"[TRACK_EVENT] session_id={session_id[:20] if session_id else 'NONE'}...")
    print(f"[TRACK_EVENT] user_id={user_id}, event_type={event_type}")
    print(f"[TRACK_EVENT] payload={payload}")

    if not session_id:
        print("[TRACK_EVENT] ABORT — no session_id")
        return

    result = AuthGateway.send_event(
        session_id=session_id,
        user_id=user_id,
        event_type=event_type,
        payload=payload
    )
    print(f"[TRACK_EVENT] Flask response: {result}")
    return result


