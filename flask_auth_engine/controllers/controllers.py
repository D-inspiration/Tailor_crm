"""controllers/auth_controller.py"""
from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from services.services import SubscriptionService
from engine.engine import EventRouter
from middleware.middleware import require_service_auth, rate_limit
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

    # REMOVED: SubscriptionGuard check — now handled in SessionService.create()
    # sub_ok, sub_reason = SubscriptionGuard.validate(user.id, "sessions")
    # if not sub_ok:
    #     return jsonify({"status": "deny", "reason": sub_reason}), 403

    result = EventRouter.dispatch(
        event_type="login",
        session_id="",            # Login creates the session, no prior session_id
        user_id=user.id,
        payload={
            "fingerprint_hash": data["fingerprint_hash"],
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
        }
    )
    session = result["session"]
    SubscriptionService.increment(user.id, "sessions")  # Track usage, don't block

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

    from services.services import SessionService
    SessionService.revoke(session_id)
    return jsonify({"status": "ok", "revoked": session_id}), 200


"""controllers/event_controller.py"""
from flask import Blueprint, request, jsonify, g
from engine.engine import EventRouter, SessionGuard, SubscriptionGuard
from middleware.middleware import require_service_auth, require_valid_session, rate_limit
from services.services import RiskService
from models.models import RISK_BLOCKED, RISK_THROTTLED
from utils.validators import require_fields
from utils.logger import get_logger

event_bp = Blueprint("event", __name__, url_prefix="/event")
logger = get_logger("EventController")


@event_bp.route("/process", methods=["POST"])
@require_service_auth
@require_valid_session
@rate_limit(max_calls=200, window_seconds=60)
def process_event():
    data = request.get_json(silent=True) or {}
    missing = require_fields(data, ["event_type", "session_id", "user_id"])
    if missing:
        return jsonify({"error": f"Missing field: {missing}"}), 400

    session_id = data["session_id"]
    user_id = data["user_id"]
    event_type = data["event_type"]
    payload = data.get("payload", {})

    # ── Subscription guard ────────────────────────────────────────────────
    sub_ok, sub_reason = SubscriptionGuard.validate(user_id, "api_calls")
    if not sub_ok:
        return jsonify({"status": "deny", "reason": sub_reason}), 403

    # ── Risk guard ────────────────────────────────────────────────────────
    risk_status = RiskService.get_status(session_id)
    if risk_status == RISK_BLOCKED:
        return jsonify({"status": "deny", "reason": "risk_blocked"}), 403
    if risk_status == RISK_THROTTLED:
        return jsonify({"status": "throttle", "reason": "risk_throttled"}), 429

    # ── Dispatch ──────────────────────────────────────────────────────────
    try:
        result = EventRouter.dispatch(event_type, session_id, user_id, payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Re-read risk score after processing (ActionEvent may have updated it)
    risk = RiskService.get_or_create(user_id, session_id)

    return jsonify({
        "status": "allow",
        "session_id": session_id,
        "risk_score": risk.score,
        "risk_status": risk.status,
        "result": result,
    }), 200


"""controllers/session_controller.py"""
from flask import Blueprint, request, jsonify
from services.services import SessionService
from middleware.middleware import require_service_auth
from utils.logger import get_logger

session_bp = Blueprint("session", __name__, url_prefix="/session")
logger = get_logger("SessionController")


@session_bp.route("/validate", methods=["POST"])
@require_service_auth
def validate():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    user_id = data.get("user_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400

    from engine.engine import SessionGuard
    valid, reason = SessionGuard.validate(session_id, user_id)
    status = "allow" if valid else "deny"
    return jsonify({"status": status, "session_id": session_id, "reason": reason}), 200


@session_bp.route("/revoke", methods=["POST"])
@require_service_auth
def revoke():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    SessionService.revoke(session_id)
    return jsonify({"status": "ok", "revoked": session_id}), 200


@session_bp.route("/revoke-all", methods=["POST"])
@require_service_auth
def revoke_all():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    count = SessionService.revoke_all_for_user(user_id)
    return jsonify({"status": "ok", "revoked_count": count}), 200


@session_bp.route("/list", methods=["POST"])
@require_service_auth
def list_sessions():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    sessions = SessionService.get_active_for_user(user_id)
    return jsonify({"sessions": [s.to_dict() for s in sessions]}), 200


"""controllers/webhook_controller.py — Receives Monnify billing webhooks."""
from flask import Blueprint, request, jsonify
from engine.engine import EventRouter
from utils.hash import hmac_sha256, constant_time_compare
from utils.logger import get_logger
from config import Config

webhook_bp = Blueprint("webhook", __name__, url_prefix="/webhook")
logger = get_logger("WebhookController")


@webhook_bp.route("/monnify", methods=["POST"])
def monnify():
    """
    Idempotent Monnify webhook handler.
    Validates HMAC, then fires a BillingEvent.
    """
    signature = request.headers.get("X-Monnify-Signature", "")
    body = request.get_data(as_text=True)
    expected = hmac_sha256(Config.DJANGO_SHARED_SECRET, body)

    if not constant_time_compare(signature, expected):
        logger.warning("Invalid Monnify signature")
        return jsonify({"error": "invalid_signature"}), 401

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    result = EventRouter.dispatch(
        event_type="billing",
        session_id="webhook",        # Billing events aren't session-bound
        user_id=user_id,
        payload=data,
    )
    return jsonify({"status": "ok", "result": result}), 200
