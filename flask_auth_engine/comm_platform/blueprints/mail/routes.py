"""
Mail dashboard API — inbox, sent, read, search, archive, composer.
"""

from flask import Blueprint, request, jsonify
from ...services.mail_service import MailService
from ...services.mail_sender_service import MailSenderService
from ...core.auth import DashboardAuth

mail_bp = Blueprint("comm_mail", __name__)


# ------------------------------------------------------------------
# Inbox
# ------------------------------------------------------------------

@mail_bp.route("/inbox", methods=["GET"])
def inbox():
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    service = MailService()
    messages = service.inbox(limit=limit, offset=offset)
    return jsonify({
        "messages": [
            {
                "id": m.id,
                "sender": m.sender,
                "recipient": m.recipient,
                "subject": m.subject,
                "preview": m.preview,
                "status": m.status,
                "received_at": m.received_at.isoformat(),
                "attachment_count": m.attachment_count,
                "is_spam": m.is_spam,
            }
            for m in messages
        ],
        "stats": service.stats(),
    })


@mail_bp.route("/<int:message_id>", methods=["GET"])
def get_message(message_id: int):
    service = MailService()
    msg = service.get(message_id)
    if not msg:
        return jsonify({"error": "Message not found"}), 404
    return jsonify({
        "id": msg.id,
        "sender": msg.sender,
        "recipient": msg.recipient,
        "subject": msg.subject,
        "body": msg.body,
        "html": msg.html,
        "status": msg.status,
        "received_at": msg.received_at.isoformat(),
        "links": msg.extract_links(),
        "attachments": [
            {"filename": a.filename, "mime_type": a.mime_type, "size": a.size_bytes}
            for a in msg.attachments
        ],
    })


@mail_bp.route("/<int:message_id>/read", methods=["POST"])
def mark_read(message_id: int):
    service = MailService()
    try:
        msg = service.mark_read(message_id)
        return jsonify({"id": msg.id, "status": msg.status})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@mail_bp.route("/<int:message_id>/archive", methods=["POST"])
def archive_message(message_id: int):
    service = MailService()
    try:
        msg = service.archive(message_id)
        return jsonify({"id": msg.id, "status": msg.status})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404


@mail_bp.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Query required"}), 400
    service = MailService()
    results = service.search(query)
    return jsonify({
        "query": query,
        "count": len(results),
        "messages": [
            {"id": m.id, "sender": m.sender, "subject": m.subject, "preview": m.preview}
            for m in results
        ],
    })


# ------------------------------------------------------------------
# Sent Messages (NEW)
# ------------------------------------------------------------------

@mail_bp.route("/sent", methods=["GET"])
def sent_messages():
    """List sent messages with optional sender/domain filter."""
    sender = request.args.get("sender")
    domain = request.args.get("domain")
    category = request.args.get("category")
    limit = request.args.get("limit", 50, type=int)

    from ...repositories.sent_message_repo import SentMessageRepository
    repo = SentMessageRepository()

    if sender:
        msgs = repo.by_sender(sender, limit)
    elif domain:
        msgs = repo.by_domain(domain, limit)
    else:
        msgs = repo.recent(limit)

    return jsonify({
        "messages": [
            {
                "id": m.id,
                "to": m.to_email,
                "from": m.from_email,
                "from_name": m.from_name,
                "subject": m.subject,
                "status": m.status,
                "category": m.category,
                "tags": m.tags,
                "sent_at": m.sent_at.isoformat(),
                "resend_id": m.resend_message_id,
            }
            for m in msgs
        ],
        "grouped_by_sender": repo.group_by_sender(),
        "grouped_by_domain": repo.group_by_domain(),
    })

@mail_bp.route("/senders", methods=["GET"])
def sender_groups():
    from ...repositories.sent_message_repo import SentMessageRepository
    repo = SentMessageRepository()
    by_sender = repo.group_by_sender()
    total = sum(g["count"] for g in by_sender)
    return jsonify({
        "total_sent": total,
        "by_sender": by_sender,
        "by_domain": repo.group_by_domain(),
    })
    
# ------------------------------------------------------------------
# Composer — Send Email (NEW)
# ------------------------------------------------------------------

@mail_bp.route("/send", methods=["POST"])
@DashboardAuth.require
def send_email():
    """
    Send an email via Resend API.
    Body: {
        "to": "recipient@example.com",
        "subject": "Hello",
        "from": "admin@atrivix.com",
        "from_name": "Atrivix",
        "html": "<p>Body</p>",
        "text": "Plain text body",
        "category": "marketing",
        "tags": ["campaign-june"]
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    to = data.get("to")
    if not to:
        return jsonify({"error": "Recipient 'to' is required"}), 400

    subject = data.get("subject", "")
    if not subject:
        return jsonify({"error": "Subject is required"}), 400

    service = MailSenderService()
    try:
        sent = service.send(
            to=to,
            subject=subject,
            from_email=data.get("from", "admin@atrivix.com"),
            from_name=data.get("from_name"),
            body_html=data.get("html"),
            body_text=data.get("text"),
            category=data.get("category", "transactional"),
            tags=data.get("tags", []),
        )
        return jsonify({
            "status": "sent",
            "id": sent.id,
            "resend_id": sent.resend_message_id,
            "to": sent.to_email,
            "from": sent.from_email,
            "subject": sent.subject,
        }), 201
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {e}"}), 500

