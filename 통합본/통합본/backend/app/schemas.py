"""
요청/응답 Pydantic 스키마.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ===== 인증 =====
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    email: EmailStr


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    success: bool = True
    message: str = ""


# ===== 지갑 (입출금/잔고) =====
class AmountRequest(BaseModel):
    amount: int = Field(gt=0, description="1원 이상의 정수")


class BalanceResponse(BaseModel):
    krw_balance: float
    frozen_balance: float


class TransactionResponse(BaseModel):
    id: int
    transaction_type: str  # DEPOSIT / WITHDRAW
    amount: float
    balance_after: float
    created_at: datetime


# ===== 대시보드 =====
class CoinTicker(BaseModel):
    coin: str
    price: float
    rate: float


class DashboardSummary(BaseModel):
    total_asset: float
    krw: float
    coin_value: float
    profit_rate: float
    auto_status: str


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    coins: list[CoinTicker]
    recent_transactions: list[TransactionResponse]


class Candle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class CandlesResponse(BaseModel):
    coin: str
    interval: str
    candles: list[Candle]


# ===== 설정 (API 키) =====
class ApiKeyRequest(BaseModel):
    access_key: str = Field(min_length=1)
    secret_key: str = Field(min_length=1)


class ApiKeyStatusResponse(BaseModel):
    registered: bool
    access_key_masked: str | None = None
