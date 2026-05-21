"""Authentication endpoints."""
from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from services.subscription_service import SubscriptionService
from engine.event_router import EventRouter
from middleware.service_auth import require_service_auth
from middleware.rate_limit import rate_limit
from utils.validators import require_fields, is_valid_email
from utils.logger import get_logger

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = get_logger("AuthController")


@auth_bp.route("/register", methods=["POST"])
@require_service_auth
@rate_limit(max_calls=20, window_seconds=60)
def register():
    data = request.get_json(silent=True) or {}
    missing = require_fields(data, ["email", "phone", "password"])
    if missing:
        return jsonify({"error": f"Missing field: {missing}"}), 400
    if not is_valid_email(data["email"]):
        return jsonify({"error": "Invalid email"}), 400
    try:
        user = AuthService.register(data["email"], data["phone"], data["password"])
        SubscriptionService.get_or_create(user.id)
        return jsonify({"user": user.to_public()}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@auth_bp.route("/login", methods=["POST"])
@require_service_auth
@rate_limit(max_calls=30, window_seconds=60)
def login():
    data = request.get_json(silent=True) or {}
    missing = require_fields(data, ["email", "password", "fingerprint_hash"])
    if missing:
        return jsonify({"error": f"Missing field: {missing}"}), 400

    ok, user = AuthService.authenticate(data["email"], data["password"])
    if not ok:
        return jsonify({"status": "deny", "reason": "invalid_credentials"}), 401

    result = EventRouter.dispatch(
        event_type="login",
        session_id="",  # Login creates the session
        user_id=user.id,
        payload={
            "fingerprint_hash": data["fingerprint_hash"],
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
        },
    )
    session = result["session"]
    SubscriptionService.increment(user.id, "sessions")

    logger.info("User %s logged in, session %s", user.id, session["id"][:8])
    return jsonify({
        "status": "allow",
        "session_id": session["id"],
        "user": user.to_public(),
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@require_service_auth
def logout():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    from services.session_service import SessionService
    SessionService.revoke(session_id)
    return jsonify({"status": "ok", "revoked": session_id}), 200
