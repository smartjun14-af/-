"""대시보드 데이터 집계 엔드포인트 (인증 필요)."""
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CoinBalance, User
from ..schemas import (
    Candle,
    CandlesResponse,
    CoinTicker,
    DashboardResponse,
    DashboardSummary,
    TransactionResponse,
)
from ..services import market_service, wallet_service

router = APIRouter(prefix="/api", tags=["dashboard"])

DEFAULT_COINS = ["BTC", "ETH", "XRP", "SOL"]


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    balance = wallet_service.get_or_create_balance(db, user)
    krw = float(balance.krw_balance)

    # 사용자 지정 코인 목록(JSON) 또는 기본값
    coins = DEFAULT_COINS
    if user.dashboard_coinlist:
        try:
            parsed = json.loads(user.dashboard_coinlist)
            if isinstance(parsed, list) and parsed:
                coins = parsed
        except (ValueError, TypeError):
            pass

    tickers = market_service.get_tickers(coins)
    price_map = {t["coin"]: t["price"] for t in tickers}

    # 보유 코인 평가액 / 매수금액 합산
    coin_value = 0.0
    buy_value = 0.0
    for row in db.query(CoinBalance).filter(CoinBalance.user_id == user.id).all():
        price = price_map.get(row.coin, float(row.avg_buy_price))
        coin_value += float(row.quantity) * price
        buy_value += float(row.quantity) * float(row.avg_buy_price)

    total_asset = krw + coin_value
    profit_rate = ((coin_value - buy_value) / buy_value * 100) if buy_value > 0 else 0.0

    summary = DashboardSummary(
        total_asset=total_asset,
        krw=krw,
        coin_value=coin_value,
        profit_rate=round(profit_rate, 2),
        auto_status="OFF",  # 자동매매 미구현 (추후 연동)
    )

    txs = wallet_service.recent_transactions(db, user, limit=5)
    recent = [
        TransactionResponse(
            id=t.id,
            transaction_type=t.transaction_type,
            amount=float(t.amount),
            balance_after=float(t.balance_after),
            created_at=t.created_at,
        )
        for t in txs
    ]

    return DashboardResponse(
        summary=summary,
        coins=[CoinTicker(**t) for t in tickers],
        recent_transactions=recent,
    )


@router.get("/candles", response_model=CandlesResponse)
def get_candles(
    coin: str = Query("BTC", description="코인 심볼 (BTC/ETH/XRP/SOL/DOGE)"),
    interval: str = Query("day", description="day/week/minute1~minute240"),
    count: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """차트용 과거 시세(캔들). 오래된→최신 순으로 반환."""
    candles = market_service.get_candles(coin, interval, count)
    return CandlesResponse(
        coin=coin,
        interval=interval,
        candles=[Candle(**c) for c in candles],
    )
