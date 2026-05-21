"""Authentication service — credential validation only."""
from typing import Optional, Tuple
from models.user import User
from utils.hash import sha256
from utils.logger import get_logger
from utils.extensions import db

logger = get_logger("AuthService")


class AuthService:
    """Handles user registration and credential verification."""

    @staticmethod
    def register(email: str, phone: str, raw_password: str) -> User:
        """Create a new user. Raises ValueError if email exists."""
        existing = User.query.filter_by(email=email.lower().strip()).first()
        if existing:
            raise ValueError(f"Email already registered: {email}")
        user = User(
            email=email.lower().strip(),
            phone=phone,
            password_hash=sha256(raw_password),
        )
        db.session.add(user)
        db.session.commit()
        logger.info("User registered: %s (id=%s)", user.email, user.id)
        return user

    @staticmethod
    def authenticate(email: str, raw_password: str) -> Tuple[bool, Optional[User]]:
        """Verify credentials. Returns (success, user_or_none)."""
        user = User.query.filter_by(email=email.lower().strip()).first()
        if not user or not user.is_active:
            return False, None
        if not user.check_password(raw_password):
            return False, None
        return True, user

    @staticmethod
    def get_user(user_id: int) -> Optional[User]:
        """Fetch user by primary key."""
        return db.session.get(User, user_id)
