"""
Authorization 헤더의 Bearer 토큰을 검증하고
현재 로그인 사용자(User)를 반환.
"""
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from .database import get_db
from .exceptions import InactiveUserError, InvalidTokenError
from .models import User
from .security import decode_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise InvalidTokenError("인증 토큰이 필요합니다.")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)  # 만료 또는 위조 시 예외
    except Exception:
        raise InvalidTokenError()

    if payload.get("type") != "access":
        raise InvalidTokenError()

    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise InvalidTokenError()

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise InvalidTokenError()
    if not user.is_active:
        raise InactiveUserError()
    return user
