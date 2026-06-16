"""
보안 유틸리티.
- 비밀번호: bcrypt 해싱
- 토큰: JWT (access / refresh)
- API 키: AES-256-GCM 대칭키 암호화
"""
import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import get_settings

settings = get_settings()


# ===== 비밀번호 (bcrypt) =====
def _pw_bytes(plain: str) -> bytes:
    return plain.encode("utf-8")[:72]


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_pw_bytes(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_pw_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ===== JWT =====
def create_access_token(subject, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": str(subject), "type": "refresh", "iat": now, "exp": expires}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires


def decode_token(token: str) -> dict:
    """만료/위조 시 jwt 예외 발생."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def hash_token(token: str) -> str:
    """refresh 토큰은 평문 대신 sha256 해시로 DB 저장."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ===== AES-256-GCM (API 키 암호화) =====
def _aes_key() -> bytes:
    # 시크릿을 sha256으로 정규화하여 32바이트(256bit) 키 생성
    return hashlib.sha256(settings.api_key_encryption_secret.encode("utf-8")).digest()


def encrypt_secret(plaintext: str) -> str:
    aesgcm = AESGCM(_aes_key())
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_secret(token: str) -> str:
    raw = base64.b64decode(token)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(_aes_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
