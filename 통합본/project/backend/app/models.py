"""
ORM 모델 

"""
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# SQLite: Integer(rowid 별칭, 자동증가) / 그 외 DB: BigInteger
BigIntId = BigInteger().with_variant(Integer, "sqlite")


class User(Base):
    __tablename__ = "users"

    id = Column(BigIntId, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt 해시
    is_active = Column(Boolean, nullable=False, default=True)
    dashboard_coinlist = Column(Text, nullable=True)  # JSON 배열 문자열 (대시보드 코인 목록)
    role = Column(String(20), nullable=False, default="USER")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    balance = relationship(
        "Balance", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    coin_balances = relationship(
        "CoinBalance", back_populates="user", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    api_key = relationship(
        "ApiKey", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(BigIntId, primary_key=True, autoincrement=True)
    user_id = Column(
        BigIntId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash = Column(String(255), nullable=False, index=True)  # sha256(refresh token)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class Balance(Base):
    __tablename__ = "balances"

    id = Column(BigIntId, primary_key=True, autoincrement=True)
    user_id = Column(
        BigIntId,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    krw_balance = Column(Numeric(20, 2), nullable=False, default=0)
    frozen_balance = Column(Numeric(20, 2), nullable=False, default=0)  # 미체결 주문 등에 묶인 금액
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    user = relationship("User", back_populates="balance")


class CoinBalance(Base):
    __tablename__ = "coin_balances"

    id = Column(BigIntId, primary_key=True, autoincrement=True)
    user_id = Column(
        BigIntId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    coin = Column(String(20), nullable=False)
    quantity = Column(Numeric(30, 8), nullable=False, default=0)
    frozen_quantity = Column(Numeric(30, 8), nullable=False, default=0)
    avg_buy_price = Column(Numeric(20, 2), nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    __table_args__ = (UniqueConstraint("user_id", "coin", name="uq_user_coin"),)

    user = relationship("User", back_populates="coin_balances")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(BigIntId, primary_key=True, autoincrement=True)
    user_id = Column(
        BigIntId, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_type = Column(String(20), nullable=False)  # DEPOSIT / WITHDRAW
    amount = Column(Numeric(20, 2), nullable=False)
    balance_after = Column(Numeric(20, 2), nullable=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    user = relationship("User", back_populates="transactions")


class ApiKey(Base):
    """업비트 API 키 (AES-256-GCM으로 암호화하여 저장)."""

    __tablename__ = "api_keys"

    id = Column(BigIntId, primary_key=True, autoincrement=True)
    user_id = Column(
        BigIntId,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    access_key_enc = Column(Text, nullable=False)
    secret_key_enc = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    user = relationship("User", back_populates="api_key")
