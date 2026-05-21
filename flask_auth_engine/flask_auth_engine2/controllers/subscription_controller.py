"""Subscription management endpoints."""
from flask import Blueprint, request, jsonify
from services.subscription_service import SubscriptionService
from middleware.service_auth import require_service_auth
from utils.logger import get_logger
from utils.extensions import db

subscription_bp = Blueprint("subscription", __name__, url_prefix="/subscription")
logger = get_logger("SubscriptionController")


@subscription_bp.route("/status", methods=["POST"])
@require_service_auth
def status():
    """Get current subscription status and usage for a user."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    sub = SubscriptionService.get_or_create(user_id)
    return jsonify({
        "status": "ok",
        "subscription": sub.to_dict(),
    }), 200


@subscription_bp.route("/upgrade", methods=["POST"])
@require_service_auth
def upgrade():
    """Upgrade user to a new plan."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    new_plan = data.get("plan", "pro")
    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    sub = SubscriptionService.update_plan(user_id, new_plan)
    return jsonify({
        "status": "ok",
        "subscription": sub.to_dict(),
    }), 200


@subscription_bp.route("/set_usage", methods=["POST"])
@require_service_auth
def set_usage():
    """Manually set usage counters (admin/override)."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    resource = data.get("resource")
    amount = data.get("amount", 0)
    if not user_id or not resource:
        return jsonify({"error": "user_id and resource required"}), 400

    sub = SubscriptionService.get_or_create(user_id)
    new_usage = dict(sub.usage)          # ← COPY dict
    new_usage[resource] = amount         # ← mutate copy
    sub.usage = new_usage                # ← REPLACE (SQLAlchemy detects this)
    db.session.commit()
    logger.info("Usage set: user=%s resource=%s amount=%s", user_id, resource, amount)
    return jsonify({
        "status": "ok",
        "subscription": sub.to_dict(),
    }), 200

    