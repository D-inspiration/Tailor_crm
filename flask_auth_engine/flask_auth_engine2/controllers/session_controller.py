"""Session management endpoints."""
from flask import Blueprint, request, jsonify
from services.session_service import SessionService
from middleware.service_auth import require_service_auth
from engine.session_guard import SessionGuard
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
