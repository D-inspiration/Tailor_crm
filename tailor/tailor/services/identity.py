# services/identity.py
from django.http import HttpRequest

def get_flask_user_id(request: HttpRequest) -> int:
    """
    SINGLE source of truth for Flask identity mapping.
    """
    flask_user_id = request.session.get("flask_user_id")

    if flask_user_id is None:
        flask_user_id = request.user.id
        request.session["flask_user_id"] = flask_user_id

    return int(flask_user_id)