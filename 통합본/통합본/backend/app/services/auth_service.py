"""
인증 비즈니스 로직.
- 회원가입: 이메일 중복 검사 → bcrypt 해싱 → users/balances 행 생성
- 로그인: 자격 검증 → JWT access + refresh 발급 (refresh는 해시로 DB 저장)
- 재발급/로그아웃
"""
import json
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from ..models import Balance, RefreshToken, User
from ..security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)

settings = get_settings()
DEFAULT_COINS = ["BTC", "ETH", "XRP", "SOL"]


def _as_aware_utc(dt: datetime) -> datetime:
    """SQLite는 tz 정보를 보존하지 않으므로 naive datetime을 UTC로 간주."""
    if dt is None:
        return dt
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def register_user(db: Session, email: str, password: str) -> User:
    email = email.strip().lower()

    if db.query(User).filter(User.email == email).first():
        raise EmailAlreadyExistsError()

    user = User(
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        role="USER",
        dashboard_coinlist=json.dumps(DEFAULT_COINS),
    )
    db.add(user)
    try:
        db.flush()  # user.id 확보 + 동시성으로 인한 unique 위반 감지
    except IntegrityError as exc:
        db.rollback()
        # 이메일 유니크 위반(동시 가입 경쟁)인 경우에만 409로 변환한다.
        # 그 외 무결성 오류(예: 스키마/제약 문제)는 숨기지 않고 그대로 올려
        # 500으로 드러나게 한다. (무조건 409로 바꾸면 실제 버그가 "이메일 중복"으로 위장됨)
        msg = str(getattr(exc, "orig", exc)).lower()
        if "email" in msg or "unique" in msg:
            raise EmailAlreadyExistsError()
        raise

    # 1:1 잔고 행 생성 (초기 가상 원화)
    db.add(
        Balance(
            user_id=user.id,
            krw_balance=settings.new_user_initial_krw,
            frozen_balance=0,
        )
    )
    db.commit()
    db.refresh(user)
    return user


def _issue_tokens(db: Session, user: User) -> tuple[str, str]:
    access = create_access_token(user.id, extra={"email": user.email})
    refresh, expires = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=expires,
            revoked=False,
        )
    )
    db.commit()
    return access, refresh


def login_user(db: Session, email: str, password: str) -> tuple[User, str, str]:
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    # 사용자 부재 / 비밀번호 불일치를 동일 메시지로 처리 (계정 존재 여부 노출 방지)
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    if not user.is_active:
        raise InactiveUserError()

    access, refresh = _issue_tokens(db, user)
    return user, access, refresh


def refresh_access_token(db: Session, refresh_token: str) -> str:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise InvalidTokenError()

    if payload.get("type") != "refresh":
        raise InvalidTokenError()

    record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_token(refresh_token))
        .first()
    )
    if not record or record.revoked:
        raise InvalidTokenError()
    if _as_aware_utc(record.expires_at) < datetime.now(timezone.utc):
        raise InvalidTokenError()

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise InvalidTokenError()

    return create_access_token(user.id, extra={"email": user.email})


def logout(db: Session, refresh_token: str) -> None:
    record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_token(refresh_token))
        .first()
    )
    if record:
        record.revoked = True
        db.commit()
