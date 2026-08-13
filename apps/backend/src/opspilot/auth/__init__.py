"""User authentication domain services and repositories."""

from opspilot.auth.repositories import (
    AuthRepository,
    AuthSessionRecord,
    UserRecord,
)
from opspilot.auth.service import (
    AuthError,
    AuthResult,
    AuthService,
    normalize_email,
)
from opspilot.auth.sqlite import SQLiteAuthRepository

__all__ = [
    "AuthError",
    "AuthRepository",
    "AuthResult",
    "AuthService",
    "AuthSessionRecord",
    "SQLiteAuthRepository",
    "UserRecord",
    "normalize_email",
]
