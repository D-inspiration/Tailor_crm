"""
Webhook gateway — receives inbound emails from providers.
Resend: POST /webhooks/resend/inbound
Future: /webhooks/ses/inbound, /webhooks/postal/inbound
"""

from flask import Blueprint, request, jsonify
from ...services.webhook_service import WebhookService

webhooks_bp = Blueprint("comm_webhooks", __name__)


@webhooks_bp.route("/resend/inbound", methods=["POST"])
def resend_inbound():
    """
    Resend inbound email webhook.
    Headers:
        Authorization: Bearer <secret>
        User-Agent: Resend
    Body: Resend inbound JSON payload
    """
    raw_body = request.get_data()
    payload = request.get_json(force=True, silent=True) or {}
    signature = request.headers.get("Authorization", "")
    headers = dict(request.headers)

    service = WebhookService()
    result = service.process(raw_body, payload, signature, headers)

    if result["status"] == "rejected":
        return jsonify(result), 401
    return jsonify(result), 201


@webhooks_bp.route("/ses/inbound", methods=["POST"])
def ses_inbound():
    """AWS SES inbound stub — polymorphic route ready."""
    raw_body = request.get_data()
    payload = request.get_json(force=True, silent=True) or {}
    signature = request.headers.get("x-amz-sns-signature", "")
    headers = dict(request.headers)

    service = WebhookService()
    result = service.process(raw_body, payload, signature, headers)

    if result["status"] == "rejected":
        return jsonify(result), 401
    return jsonify(result), 201
