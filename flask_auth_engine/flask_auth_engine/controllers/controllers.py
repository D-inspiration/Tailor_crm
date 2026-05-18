"""controllers/auth_controller.py"""
from flask import Blueprint, request, jsonify
from services.auth_service import AuthService
from services.services import SubscriptionService
from engine.engine import EventRouter
from middleware.middleware import require_service_auth, rate_limit
from utils.validators import require_fields, is_valid_email
from utils.logger import get_logger
from store import users, subscriptions, events, risks, fingerprints
from store import sessions as session_store
from models.models import DEFAULT_LIMITS, SUB_ACTIVE
from datetime import datetime, timezone, timedelta


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
    
    print(f"[AUTH REGISTER] Attempting to register: {data['email']}")
    
    try:
        user = AuthService.register(data["email"], data["phone"], data["password"])
        print(f"[AUTH REGISTER] Created user: id={user.id}, email={user.email}")
        
        sub = SubscriptionService.get_or_create(user.id)
        print(f"[AUTH REGISTER] Subscription for user {user.id}: plan={sub.plan}")
        
        return jsonify({"user": user.to_public()}), 201
    except ValueError as e:
        print(f"[AUTH REGISTER] ValueError: {e}")
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        print(f"[AUTH REGISTER] Exception: {type(e).__name__}: {e}")
        return jsonify({"error": "registration_failed"}), 500


@auth_bp.route("/login", methods=["POST"])
@require_service_auth
@rate_limit(max_calls=30, window_seconds=60)
def login():
    data = request.get_json(silent=True) or {}
    missing = require_fields(data, ["email", "password", "fingerprint_hash"])
    if missing:
        return jsonify({"error": f"Missing field: {missing}"}), 400

    print(f"[AUTH LOGIN] Attempting login: {data['email']}")
    
    ok, user = AuthService.authenticate(data["email"], data["password"])
    print(f"[AUTH LOGIN] AuthService.authenticate returned: ok={ok}, user={user}")
    
    if not ok:
        print(f"[AUTH LOGIN] Authentication failed for {data['email']}")
        return jsonify({"status": "deny", "reason": "invalid_credentials"}), 401

    print(f"[AUTH LOGIN] User authenticated: id={user.id}, email={user.email}")

    # Around line 66 in controllers.py
    result = EventRouter.dispatch(
        "login",  # event_type
        "",       # session_id
        user.id,  # user_id
        {         # payload
            "fingerprint_hash": data["fingerprint_hash"],
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent"),
        }
    )
    
    session = result["session"]
    
    print(f"[AUTH LOGIN] Session created: {session['id'][:8]} for user {user.id}")

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

    session_id = data.get("session_id")
    user_id = data.get("user_id")
    event_type = data.get("event_type")
    payload = data.get("payload", {})

    if not event_type:
        return jsonify({"error": "Missing field: event_type"}), 400

    # FIX BUG 1: Use `is None` — not `not` — so user_id=0 (first Flask user) is accepted.
    # The original code used falsy checks, which blocked every event from user_id=0
    # because `not 0 == True`. This caused the increment endpoint to return 400,
    # so usage was never recorded, and Flask's counter stayed at 0 while Django's
    # Customer.objects.count() grew — producing the "different numbers" desync.
    if session_id is None and user_id is None:
        return jsonify({"error": "Missing field: session_id or user_id"}), 400

    # If no user_id but session_id exists, resolve user from session
    if user_id is None and session_id is not None:
        from store import sessions as session_store
        session = session_store.get(session_id)
        if not session:
            return jsonify({"error": "session_not_found"}), 404
        user_id = session.user_id

    sub_ok, sub_reason = SubscriptionGuard.validate(user_id, "api_calls")
    if not sub_ok:
        return jsonify({"status": "deny", "reason": sub_reason}), 403

    if session_id:
        risk_status = RiskService.get_status(session_id)
        if risk_status == RISK_BLOCKED:
            return jsonify({"status": "deny", "reason": "risk_blocked"}), 403
        if risk_status == RISK_THROTTLED:
            return jsonify({"status": "throttle", "reason": "risk_throttled"}), 429

    try:
        result = EventRouter.dispatch(event_type, session_id or "server", user_id, payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    risk = RiskService.get_or_create(user_id, session_id) if session_id else None

    return jsonify({
        "status": "allow",
        "session_id": session_id or "server",
        "risk_score": risk.score if risk else 0,
        "risk_status": risk.status if risk else "ok",
        "result": result,
    }), 200


@event_bp.route("/subscription/increment", methods=["POST"])
@require_service_auth
def increment_subscription_usage():
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    resource = data.get("resource")

    # FIX BUG 1 (same issue): user_id=0 is valid — must use `is None`
    if user_id is None or not resource:
        return jsonify({"error": "Missing user_id or resource"}), 400

    try:
        current_usage = SubscriptionGuard.get_usage(user_id, resource)
        new_usage = current_usage + 1
        SubscriptionGuard.set_usage(user_id, resource, new_usage)

        return jsonify({
            "status": "ok",
            "resource": resource,
            "previous": current_usage,
            "current": new_usage,
        }), 200

    except Exception as e:
        import traceback
        logger.error("increment_subscription_usage error: %s\n%s", e, traceback.format_exc())
        return jsonify({"error": "internal_server_error", "detail": str(e)}), 500


@event_bp.route("/subscription/set_usage", methods=["POST"])
@require_service_auth
def set_subscription_usage():
    """
    Hard-set a usage counter to an exact value.
    Called by Django on customer create, delete, and login to keep
    Flask's counter in sync with Django's actual DB count.
    """
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    resource = data.get("resource")
    value = data.get("value")

    # FIX: user_id=0 is valid — use `is None`
    if user_id is None or not resource or value is None:
        return jsonify({"error": "Missing user_id, resource, or value"}), 400

    try:
        value = int(value)
        if value < 0:
            return jsonify({"error": "value must be >= 0"}), 400

        SubscriptionGuard.set_usage(user_id, resource, value)

        return jsonify({
            "status": "ok",
            "resource": resource,
            "value": value,
        }), 200

    except Exception as e:
        import traceback
        logger.error("set_subscription_usage error: %s\n%s", e, traceback.format_exc())
        return jsonify({"error": "internal_server_error", "detail": str(e)}), 500


    
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
    
    # Add risk data if session is valid
    risk_status = "ok"
    risk_score = 0
    if valid:
        from services.services import RiskService
        risk = RiskService.get_or_create(user_id, session_id)
        risk_status = risk.status
        risk_score = risk.score
    
    return jsonify({
        "status": status, 
        "session_id": session_id, 
        "reason": reason,
        "risk_status": risk_status,
        "risk_score": risk_score
    }), 200


    
    
@session_bp.route("/subscription/status", methods=["POST"])
@require_service_auth
def subscription_status():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if user_id is None:
        return jsonify({"error": "user_id required"}), 400
    
    # Read directly from SQLite store
    from store import SubscriptionStore
    store = SubscriptionStore()
    sub = store.get(user_id)
    
    if not sub:
        # Return default free plan if no subscription exists
        return jsonify({
            "subscription": {
                "plan": "free",
                "status": "active",
                "limits": {"api_calls": 100, "customers": 20, "events_per_day": 500, "orders_per_month": 10, "sessions": 5, "staff_accounts": 1, "storage_mb": 50},
                "usage": {"api_calls": 0, "customers": 0, "events_per_day": 0, "orders": 0, "orders_per_month": 0, "sessions": 0, "staff_accounts": 0, "storage_mb": 0},
                "user_id": user_id
            },
            "limits": {"api_calls": 100, "customers": 20, "events_per_day": 500, "orders_per_month": 10, "sessions": 5, "staff_accounts": 1, "storage_mb": 50},
            "usage": {"api_calls": 0, "customers": 0, "events_per_day": 0, "orders": 0, "orders_per_month": 0, "sessions": 0, "staff_accounts": 0, "storage_mb": 0}
        }), 200
    
    return jsonify({
        "subscription": {
            "plan": sub.plan,
            "status": sub.status,
            "limits": sub.limits,
            "usage": sub.usage,
            "user_id": user_id
        },
        "limits": sub.limits,
        "usage": sub.usage
    }), 200

@session_bp.route("/subscription/upgrade", methods=["POST"])
@require_service_auth
def upgrade_subscription():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    plan = data.get("plan")
    
    if user_id is None or not plan:
        return jsonify({"error": "Missing user_id or plan"}), 400
    
    from store import SubscriptionStore
    store = SubscriptionStore()
    
    sub = store.get(user_id)
    if not sub:
        sub = Subscription(user_id=user_id)
    
    if plan not in DEFAULT_LIMITS:
        return jsonify({"error": f"invalid_plan: {plan}"}), 400
    
    # UPGRADE
    sub.plan = plan
    sub.limits = DEFAULT_LIMITS[plan].copy()
    sub.status = SUB_ACTIVE
    
    # SET EXPIRATION: 30 days from now for paid plans
    if plan != "free":
        sub.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    else:
        sub.expires_at = None
    
    store.save(sub)
    
    return jsonify({
        "status": "ok",
        "plan": plan,
        "limits": sub.limits,
        "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
        "days_remaining": sub.days_remaining(),
        "user_id": user_id
    }), 200

    
@session_bp.route("/subscription/cancel", methods=["POST"])
@require_service_auth
def cancel_subscription():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    
    if user_id is None:
        return jsonify({"error": "user_id required"}), 400
    
    from store import SubscriptionStore
    store = SubscriptionStore()
    sub = store.get(user_id)
    
    if not sub or sub.plan == "free":
        return jsonify({"error": "no_active_paid_subscription"}), 400
    
    sub.cancel()
    store.save(sub)
    
    return jsonify({
        "status": "cancelled",
        "plan": sub.plan,
        "access_until": sub.expires_at.isoformat() if sub.expires_at else None,
        "message": f"Cancelled. Access continues until {sub.expires_at.date() if sub.expires_at else 'N/A'}"
    }), 200
    


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
    if user_id is None:
        return jsonify({"error": "user_id required"}), 400
    count = SessionService.revoke_all_for_user(user_id)
    return jsonify({"status": "ok", "revoked_count": count}), 200


@session_bp.route("/list", methods=["POST"])
@require_service_auth
def list_sessions():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    if user_id is None:
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
