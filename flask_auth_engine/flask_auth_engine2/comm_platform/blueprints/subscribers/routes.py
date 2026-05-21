"""
Subscription authority API — audience management.
"""

from flask import Blueprint, request, jsonify
from ...services.subscription_service import SubscriptionService
from ...core.constants import SubscriberStatus

subscribers_bp = Blueprint("comm_subscribers", __name__)


@subscribers_bp.route("", methods=["GET"])
def list_subscribers():
    """List subscribers with optional filters."""
    tag = request.args.get("tag")
    plan = request.args.get("plan")
    status = request.args.get("status")

    service = SubscriptionService()
    subscribers = service.audience(
        tag=tag,
        plan=plan,
        status=SubscriberStatus(status) if status else None,
    )

    return jsonify({
        "subscribers": [
            {
                "id": s.id,
                "email": s.email,
                "status": s.status,
                "plan": s.plan,
                "tags": s.tags,
                "source": s.source,
                "created_at": s.created_at.isoformat(),
            }
            for s in subscribers
        ],
        "stats": service.stats(),
    })


@subscribers_bp.route("", methods=["POST"])
def register():
    """Register a new subscriber."""
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400

    service = SubscriptionService()
    subscriber = service.register(
        email=email,
        source=data.get("source", "api"),
        tags=data.get("tags", []),
        plan=data.get("plan", "free"),
    )

    return jsonify({
        "id": subscriber.id,
        "email": subscriber.email,
        "status": subscriber.status,
    }), 201


@subscribers_bp.route("/<email>/confirm", methods=["POST"])
def confirm(email: str):
    service = SubscriptionService()
    try:
        sub = service.confirm(email)
        return jsonify({"email": sub.email, "status": sub.status})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@subscribers_bp.route("/<email>/unsubscribe", methods=["POST"])
def unsubscribe(email: str):
    service = SubscriptionService()
    try:
        sub = service.unsubscribe(email)
        return jsonify({"email": sub.email, "status": sub.status})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@subscribers_bp.route("/<email>/plan", methods=["PUT"])
def change_plan(email: str):
    data = request.get_json(force=True, silent=True) or {}
    new_plan = data.get("plan")
    if not new_plan:
        return jsonify({"error": "Plan required"}), 400

    service = SubscriptionService()
    try:
        sub = service.change_plan(email, new_plan)
        return jsonify({"email": sub.email, "plan": sub.plan})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
