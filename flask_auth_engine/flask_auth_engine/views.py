# flask_auth_engine/views.py

from flask import request, jsonify
import store  # ✅ FIXED: no db module needed
from werkzeug.security import check_password_hash, generate_password_hash


def find_user_by_email(email):
    return store.users.get_by_email(email)


def create_user(email, password, phone=None):
    user = store.User(
        email=email.lower(),
        phone=phone,
        password_hash=generate_password_hash(password),
        is_active=True
    )
    return store.users.save(user)

bp = Blueprint("auth", __name__, url_prefix="/auth")
# ✅ THIS IS THE IMPORTANT PART
@bp.route("/auth/login", methods=["POST"])
def login_or_register():
    data = request.json

    email = data.get("email")
    password = data.get("password")
    phone = data.get("phone")

    if not email or not password:
        return jsonify({"status": "deny", "reason": "missing_fields"}), 400

    user = store.users.get_by_email(email)

    if not user:
        user = store.User(
            email=email.lower(),
            phone=phone,
            password_hash=generate_password_hash(password),
            is_active=True
        )
        user = store.users.save(user)

    if not check_password_hash(user.password_hash, password):
        return jsonify({"status": "deny", "reason": "invalid_credentials"}), 401

    return jsonify({
        "status": "allow",
        "session_id": generate_session_id(user.id),
        "user": {
            "id": user.id,
            "email": user.email,
            "phone": user.phone,
            "is_active": user.is_active
        }
    }), 200
