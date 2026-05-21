"""Billing webhook endpoints with idempotency and multi-period support."""
from flask import Blueprint, request, jsonify
from services.subscription_service import SubscriptionService
from services.billing_service import calculate_new_expiry, get_period_months, PLAN_PERIODS
from utils.hash import hmac_sha256, constant_time_compare
from utils.logger import get_logger
from utils.extensions import db
from config import Config
from models.subscription import Subscription, SUB_ACTIVE, DEFAULT_LIMITS
from models.payment import PaymentRecord
from datetime import datetime, timezone

webhook_bp = Blueprint("webhook", __name__, url_prefix="/webhook")
logger = get_logger("WebhookController")


@webhook_bp.route("/monnify", methods=["POST"])
def monnify():
    """
    Idempotent Monnify webhook handler.
    Supports: monthly, quarterly, biannual, yearly.
    """
    # ── HMAC Validation ──────────────────────────────────────────────────
    signature = request.headers.get("X-Monnify-Signature", "")
    body = request.get_data(as_text=True)
    expected = hmac_sha256(Config.DJANGO_SHARED_SECRET, body)

    if not constant_time_compare(signature, expected):
        logger.warning("Invalid Monnify signature from %s", request.remote_addr)
        return jsonify({"error": "invalid_signature"}), 401

    data = request.get_json(silent=True) or {}

    # ── Required Fields ────────────────────────────────────────────────────
    user_id = data.get("user_id")
    payment_ref = data.get("paymentReference")
    amount = data.get("amount", 0)
    plan = data.get("plan", "starter")
    period = data.get("period", "monthly")

    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    if not payment_ref:
        return jsonify({"error": "paymentReference required"}), 400

    # ── Idempotency Check ────────────────────────────────────────────────
    existing = PaymentRecord.query.filter_by(reference=payment_ref).first()
    if existing:
        logger.info("Duplicate webhook ignored: ref=%s user=%s", payment_ref, user_id)
        return jsonify({
            "status": "already_processed",
            "reference": payment_ref,
            "processed_at": existing.processed_at.isoformat() if existing.processed_at else None,
        }), 200

    # ── Validate Period ──────────────────────────────────────────────────
    if period not in PLAN_PERIODS:
        logger.warning("Unknown period '%s', defaulting to monthly", period)
        period = "monthly"

    period_months = get_period_months(period)

    # ── Record Payment ───────────────────────────────────────────────────
    payment = PaymentRecord(
        reference=payment_ref,
        user_id=user_id,
        amount=amount,
        plan=plan,
        period_months=period_months,
        status="completed",
        raw_payload=data,
    )
    db.session.add(payment)

    # ── Extend Subscription ──────────────────────────────────────────────
    sub = SubscriptionService.get_or_create(user_id)

    new_expires = calculate_new_expiry(sub.expires_at, period_months)

    sub.expires_at = new_expires
    sub.status = SUB_ACTIVE
    sub.plan = plan
    sub.limits = DEFAULT_LIMITS.get(plan, DEFAULT_LIMITS["free"]).copy()
    sub.usage = {k: 0 for k in sub.limits}

    db.session.commit()

    logger.info(
        "Payment processed: ref=%s user=%s amount=%s plan=%s period=%s expires=%s",
        payment_ref, user_id, amount, plan, period, new_expires.isoformat()
    )

    return jsonify({
        "status": "ok",
        "reference": payment_ref,
        "plan": plan,
        "period": period,
        "period_label": PLAN_PERIODS[period]["label"],
        "expires_at": new_expires.isoformat(),
        "message": f"Payment processed. Active until {new_expires.strftime('%B %d, %Y')}.",
    }), 200


