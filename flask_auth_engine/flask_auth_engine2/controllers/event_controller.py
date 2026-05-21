"""Event processing endpoints."""
from flask import Blueprint, request, jsonify, g
from engine.event_router import EventRouter
from engine.session_guard import SessionGuard
from engine.subscription_guard import SubscriptionGuard
from middleware.service_auth import require_service_auth
from middleware.session_auth import require_valid_session
from middleware.rate_limit import rate_limit
from services.risk_service import RiskService
from models.risk import RISK_BLOCKED, RISK_THROTTLED
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

    # Subscription guard
    sub_ok, sub_reason = SubscriptionGuard.validate(user_id, "api_calls")
    if not sub_ok:
        return jsonify({"status": "deny", "reason": sub_reason}), 403

    # Risk guard
    risk_status = RiskService.get_status(session_id)
    if risk_status == RISK_BLOCKED:
        return jsonify({"status": "deny", "reason": "risk_blocked"}), 403
    if risk_status == RISK_THROTTLED:
        return jsonify({"status": "throttle", "reason": "risk_throttled"}), 429

    # Dispatch
    try:
        result = EventRouter.dispatch(event_type, session_id, user_id, payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    risk = RiskService.get_or_create(user_id, session_id)
    return jsonify({
        "status": "allow",
        "session_id": session_id,
        "risk_score": risk.score,
        "risk_status": risk.status,
        "result": result,
    }), 200
