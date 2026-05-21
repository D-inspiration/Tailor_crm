"""
Simple dashboard authentication.
Pluggable: uses existing session auth if available, falls back to API key.
"""

import os
import functools
from flask import request, session
from werkzeug.exceptions import Unauthorized


class DashboardAuth:
    """
    Encapsulated auth for comm_platform dashboard.
    Checks in order:
    1. Existing session auth (if user already logged into main app)
    2. API key header (for standalone dashboard access)
    3. Basic password (fallback)
    """

    _api_key = None
    _password = None

    @classmethod
    def init_app(cls, app) -> None:
        cls._api_key = app.config.get("COMM_DASHBOARD_API_KEY") or os.getenv("COMM_DASHBOARD_API_KEY")
        cls._password = app.config.get("COMM_DASHBOARD_PASSWORD") or os.getenv("COMM_DASHBOARD_PASSWORD")

    @classmethod
    def check(cls) -> bool:
        """Return True if request is authenticated."""
        # 1. Existing session (your app already has session auth)
        if session.get("user_id") or session.get("authenticated") or session.get("comm_dashboard_auth"):
            return True

        # 2. API key in header: X-API-Key: <key>
        api_key = request.headers.get("X-API-Key", "")
        if cls._api_key and api_key == cls._api_key:
            return True

        # 3. Basic password in header: X-Dashboard-Password: <password>
        password = request.headers.get("X-Dashboard-Password", "")
        if cls._password and password == cls._password:
            return True

        # 4. Query param ?api_key=... (for simple browser access)
        api_key = request.args.get("api_key", "")
        if cls._api_key and api_key == cls._api_key:
            return True

        return False

    @classmethod
    def require(cls, f):
        """Decorator to protect routes."""
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if not cls.check():
                raise Unauthorized("Authentication required. Set X-API-Key header or login to main app.")
            return f(*args, **kwargs)
        return decorated
        