"""
services/auth_service.py
Owns: credential validation, login orchestration.
Does NOT create sessions — delegates to SessionService.
"""
from typing import Optional, Tuple
from models.models import User
from utils.hash import sha256
from utils.logger import get_logger
import store

logger = get_logger("AuthService")


class AuthService:

    @staticmethod
    def register(email: str, phone: str, raw_password: str) -> User:
        if store.users.get_by_email(email):
            raise ValueError(f"Email already registered: {email}")
        user = User(
            id=0,
            email=email.lower().strip(),
            phone=phone,
            password_hash=sha256(raw_password),
        )
        return store.users.save(user)

    @staticmethod
    def authenticate(email: str, raw_password: str) -> Tuple[bool, Optional[User]]:
        user = store.users.get_by_email(email)
        if not user or not user.is_active:
            return False, None
        if not user.check_password(raw_password):
            return False, None
        return True, user

    @staticmethod
    def get_user(user_id: int) -> Optional[User]:
        return store.users.get_by_id(user_id)
