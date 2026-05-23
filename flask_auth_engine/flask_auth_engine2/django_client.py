"""Django integration client for SBEAE."""
import os
import requests
from typing import Any, Dict, Optional
from dotenv import load_dotenv
load_dotenv()  # Loads .env file into os.environ

SBEAE_BASE_URL = os.getenv("SBEAE_URL", "http://127.0.0.1:5050")
SBEAE_SECRET = os.getenv("DJANGO_SHARED_SECRET")
if not SBEAE_SECRET:
    raise ValueError("DJANGO_SHARED_SECRET environment variable is required")



class SBEAEError(Exception):
    """Raised when SBEAE is unreachable or returns an error."""
    pass


class SBEAEClient:
    """Zero-dependency client (beyond requests) for Django projects."""

    def __init__(
        self,
        base_url: str = SBEAE_BASE_URL,
        secret: str = SBEAE_SECRET,
        timeout: int = 5,
    ):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Service-Secret": self.secret,
            "Content-Type": "application/json",
        }

    def _post(self, path: str, data: dict) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.post(
                url, json=data, headers=self._headers(), timeout=self.timeout
            )
            return resp.json()
        except requests.RequestException as e:
            raise SBEAEError(f"SBEAE unreachable: {e}") from e

    # ── Auth ─────────────────────────────────────────────────────────────────

    def register(self, email: str, phone: str, password: str) -> Dict[str, Any]:
        return self._post("/auth/register", {
            "email": email, "phone": phone, "password": password
        })

    def login(self, email: str, password: str, fingerprint_hash: str) -> Dict[str, Any]:
        return self._post("/auth/login", {
            "email": email,
            "password": password,
            "fingerprint_hash": fingerprint_hash,
        })

    def logout(self, session_id: str) -> Dict[str, Any]:
        return self._post("/auth/logout", {"session_id": session_id})

    # ── Sessions ─────────────────────────────────────────────────────────────

    def validate_session(self, session_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        return self._post("/session/validate", {
            "session_id": session_id,
            "user_id": user_id,
        })

    def revoke_session(self, session_id: str) -> Dict[str, Any]:
        return self._post("/session/revoke", {"session_id": session_id})

    def revoke_all_sessions(self, user_id: int) -> Dict[str, Any]:
        return self._post("/session/revoke-all", {"user_id": user_id})

    def list_sessions(self, user_id: int) -> Dict[str, Any]:
        return self._post("/session/list", {"user_id": user_id})

    # ── Events ───────────────────────────────────────────────────────────────

    def process_event(
        self, session_id: str, user_id: int, event_type: str, payload: dict = None
    ) -> Dict[str, Any]:
        return self._post("/event/process", {
            "session_id": session_id,
            "user_id": user_id,
            "event_type": event_type,
            "payload": payload or {},
        })

    # ── Convenience ──────────────────────────────────────────────────────────

    def is_allowed(self, session_id: str, user_id: int, event_type: str = "action") -> bool:
        """One-liner for Django views / DRF permission classes."""
        try:
            result = self.process_event(session_id, user_id, event_type)
            return result.get("status") == "allow"
        except SBEAEError:
            return False  # Fail closed

    # ── Billing / Webhook ────────────────────────────────────────────────────

    def process_payment_webhook(
        self,
        user_id: int,
        payment_reference: str,
        amount: float,
        plan: str = "starter",
        period: str = "monthly",
    ) -> Dict[str, Any]:
        """
        Simulate or process a payment webhook.
        Periods: monthly, quarterly, biannual, yearly
        """
        return self._post("/webhook/monnify", {
            "user_id": user_id,
            "paymentReference": payment_reference,
            "amount": amount,
            "plan": plan,
            "period": period,
        })
        
