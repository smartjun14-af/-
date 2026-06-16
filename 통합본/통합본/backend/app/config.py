"""
애플리케이션 환경설정.
.env 파일 또는 환경변수로 모든 값을 주입.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


    # 기본값은 SQLite.
    # PostgreSQL 사용 시: postgresql+psycopg2://user:pw@localhost:5432/coin
    database_url: str = "sqlite:///./coin.db"

    # ----- JWT -----
    
    jwt_secret_key: str = "CHANGE_ME_dev_secret_key_please_override_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ----- API 키 암호화 (AES-256-GCM) -----
    api_key_encryption_secret: str = "CHANGE_ME_dev_encryption_secret_min_32_chars"

    # ----- 업비트 시세 (공개 API) -----
    upbit_ticker_url: str = "https://api.upbit.com/v1/ticker"
    upbit_candles_url: str = "https://api.upbit.com/v1/candles"
    market_timeout_seconds: float = 3.0

    # ----- CORS (프론트 주소) -----
    cors_origins: list[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

    # ----- 신규 가입자 초기 가상 원화 잔고 -----
    new_user_initial_krw: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
