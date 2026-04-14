"""JWT 鉴权与用户管理服务."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from loguru import logger

from app.config import config
from app.services.database_service import database_service


ROLE_VIEWER = "viewer"
ROLE_OPERATOR = "operator"
ROLE_ADMIN = "admin"
ROLE_ORDER = {ROLE_VIEWER: 1, ROLE_OPERATOR: 2, ROLE_ADMIN: 3}


class AuthService:
    """负责默认用户、密码校验和 JWT 令牌处理."""

    def __init__(self) -> None:
        self._seeded = False

    def initialize(self) -> None:
        """确保默认账号存在."""
        if self._seeded:
            return

        database_service.initialize()
        self._ensure_user(
            config.default_viewer_username,
            config.default_viewer_password,
            ROLE_VIEWER,
        )
        self._ensure_user(
            config.default_operator_username,
            config.default_operator_password,
            ROLE_OPERATOR,
        )
        self._ensure_user(
            config.default_admin_username,
            config.default_admin_password,
            ROLE_ADMIN,
        )
        self._seeded = True

    def _ensure_user(self, username: str, password: str, role: str) -> None:
        existing = database_service.fetch_one(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        )
        if existing:
            return

        password_hash, salt = self.hash_password(password)
        database_service.execute(
            """
            INSERT INTO users (username, password_hash, password_salt, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                salt,
                role,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        logger.info(f"已创建默认账号: {username} ({role})")

    def hash_password(self, password: str, salt: str | None = None) -> tuple[str, str]:
        """使用 PBKDF2-HMAC 生成密码摘要."""
        salt = salt or os.urandom(16).hex()
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            config.password_hash_iterations,
        )
        return digest.hex(), salt

    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """校验密码."""
        computed_hash, _ = self.hash_password(password, salt=salt)
        return hmac.compare_digest(computed_hash, password_hash)

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        """校验用户名密码并返回用户信息."""
        self.initialize()
        user = database_service.fetch_one(
            """
            SELECT id, username, password_hash, password_salt, role
            FROM users
            WHERE username = ?
            """,
            (username,),
        )
        if not user:
            return None

        if not self.verify_password(password, user["password_hash"], user["password_salt"]):
            return None

        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        }

    def create_access_token(self, user: dict[str, Any]) -> str:
        """创建 HS256 JWT."""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=config.jwt_expire_minutes)
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user["username"],
            "role": user["role"],
            "user_id": user["id"],
            "exp": int(expires_at.timestamp()),
        }
        signing_input = ".".join(
            [
                self._b64_encode_json(header),
                self._b64_encode_json(payload),
            ]
        )
        signature = hmac.new(
            config.jwt_secret.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        token = f"{signing_input}.{self._b64_encode_bytes(signature)}"
        return token

    def verify_token(self, token: str) -> dict[str, Any]:
        """校验并返回 JWT 载荷."""
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
        except ValueError as exc:
            raise ValueError("令牌格式非法") from exc

        signing_input = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(
            config.jwt_secret.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        actual_sig = self._b64_decode_bytes(signature_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("令牌签名校验失败")

        payload = json.loads(self._b64_decode_bytes(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("令牌已过期")
        return payload

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """按用户名读取用户."""
        self.initialize()
        return database_service.fetch_one(
            "SELECT id, username, role FROM users WHERE username = ?",
            (username,),
        )

    def require_role(self, role: str, minimum_role: str) -> bool:
        """判断角色是否满足最小权限."""
        return ROLE_ORDER.get(role, 0) >= ROLE_ORDER.get(minimum_role, 0)

    @staticmethod
    def _b64_encode_json(payload: dict[str, Any]) -> str:
        return AuthService._b64_encode_bytes(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )

    @staticmethod
    def _b64_encode_bytes(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _b64_decode_bytes(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(f"{data}{padding}".encode("utf-8"))


auth_service = AuthService()
