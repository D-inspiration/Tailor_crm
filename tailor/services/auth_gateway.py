import requests
from django.conf import settings

FLASK_AUTH_URL = getattr(settings, 'FLASK_AUTH_URL', 'http://127.0.0.1:5050')


class AuthGateway:
    @staticmethod
    def _headers():
        return {
            "Content-Type": "application/json",
            "X-Service-Secret": getattr(settings, 'FLASK_SERVICE_KEY', 'django-flask-shared-secret')
        }

    @staticmethod
    def validate_session(session_id, user_id=None):
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/session/validate",
                json={"session_id": session_id, "user_id": user_id},
                timeout=3,
                headers=AuthGateway._headers()
            )
            return res.json()
        except Exception:
            return {"status": "deny", "reason": "auth_service_unreachable"}

    @staticmethod
    def send_event(session_id, user_id, event_type, payload):
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/event/process",
                json={
                    "event_type": event_type,
                    "session_id": session_id,
                    "user_id": user_id,
                    "payload": payload
                },
                timeout=3,
                headers=AuthGateway._headers()
            )
            return res.json()
        except Exception:
            return {"status": "deny", "reason": "event_service_down"}

    @staticmethod
    def revoke_session(session_id):
        try:
            res = requests.post(
                f"{FLASK_AUTH_URL}/session/revoke",
                json={"session_id": session_id},
                timeout=3,
                headers=AuthGateway._headers()
            )
            return res.json()
        except Exception:
            return {"status": "deny", "reason": "auth_service_unreachable"}

            

