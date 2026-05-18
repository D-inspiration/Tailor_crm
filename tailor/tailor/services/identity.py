# services/identity.py
from django.http import HttpRequest


def get_flask_user_id(request: HttpRequest, strict: bool = True) -> int | None:
    """
    Flask identity source of truth.
    
    strict=True:  Raise if missing (for subscription gates, payments, upgrades)
    strict=False: Return None if missing (for display-only, graceful degradation)
    """
    flask_user_id = request.session.get("flask_user_id")
    
    print(f"[FLASK DEBUG RAW SESSION] {flask_user_id}")

    if flask_user_id is None:
        if strict:
            raise ValueError(
                "Missing flask_user_id in session. "
                "User must authenticate with Flask first."
            )
        return None

    return int(flask_user_id)


def set_flask_identity(request, flask_data, email: str):
    user = flask_data.get("user", {})

    if not user.get("id"):
        raise ValueError("Flask response missing user.id")

    request.session["flask_user_id"] = user["id"]
    request.session["flask_email"] = email
    request.session["flask_session_id"] = flask_data.get("session_id")

    request.session.modified = True
    
    if request.session["flask_user_id"] is None:
        raise ValueError("Flask returned invalid user payload")

    
