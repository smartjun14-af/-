"""
시세 서비스: 업비트 공개 시세 API(인증 불필요)에서 현재가/등락률을 가져옵니다.
네트워크 장애 또는 API 차단 시에도 대시보드가 동작하도록 폴백 시세를 제공합니다.
"""
import logging
import random
from datetime import datetime, timedelta, timezone

import requests

from ..config import get_settings

logger = logging.getLogger("coin")
settings = get_settings()

# 심볼 → 업비트 마켓 코드
MARKET_MAP = {
    "BTC": "KRW-BTC",
    "ETH": "KRW-ETH",
    "XRP": "KRW-XRP",
    "SOL": "KRW-SOL",
    "DOGE": "KRW-DOGE",
}

# 업비트 호출 실패 시 사용할 폴백 시세 (대시보드 무중단 렌더링용)
FALLBACK = {
    "BTC": {"price": 98_500_000, "rate": 2.15},
    "ETH": {"price": 4_200_000, "rate": -0.85},
    "XRP": {"price": 820, "rate": 1.02},
    "SOL": {"price": 242_000, "rate": 3.34},
    "DOGE": {"price": 214, "rate": -1.20},
}


def get_tickers(coins: list[str]) -> list[dict]:
    markets = [MARKET_MAP[c] for c in coins if c in MARKET_MAP]
    if not markets:
        return []

    try:
        resp = requests.get(
            settings.upbit_ticker_url,
            params={"markets": ",".join(markets)},
            timeout=settings.market_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        by_market = {item["market"]: item for item in data}

        result = []
        for coin in coins:
            item = by_market.get(MARKET_MAP.get(coin))
            if item:
                result.append(
                    {
                        "coin": coin,
                        "price": float(item["trade_price"]),
                        "rate": round(float(item["signed_change_rate"]) * 100, 2),
                    }
                )
            elif coin in FALLBACK:
                result.append({"coin": coin, **FALLBACK[coin]})
        return result

    except Exception as exc:  # 네트워크/파싱 오류 → 폴백
        logger.warning("업비트 시세 조회 실패(%s). 폴백 시세를 사용합니다.", exc)
        return [{"coin": c, **FALLBACK[c]} for c in coins if c in FALLBACK]


# 차트용 캔들 단위 → 업비트 캔들 API 경로
CANDLE_INTERVAL_MAP = {
    "minute1": "minutes/1",
    "minute3": "minutes/3",
    "minute5": "minutes/5",
    "minute10": "minutes/10",
    "minute15": "minutes/15",
    "minute30": "minutes/30",
    "minute60": "minutes/60",
    "minute240": "minutes/240",
    "day": "days",
    "week": "weeks",
}

# 단위별 캔들 1개의 시간 간격(분) — 폴백 캔들 생성 시 x축 시간 계산용
_INTERVAL_MINUTES = {
    "minute1": 1, "minute3": 3, "minute5": 5, "minute10": 10, "minute15": 15,
    "minute30": 30, "minute60": 60, "minute240": 240, "day": 1440, "week": 10080,
}


def get_candles(coin: str, interval: str = "day", count: int = 30) -> list[dict]:
    """
    선택 코인의 과거 시세(캔들)를 업비트에서 조회한다(오래된→최신 순으로 정렬).
    네트워크 차단/장애 시에는 폴백 캔들을 생성해 차트가 항상 그려지도록 한다.
    """
    market = MARKET_MAP.get(coin)
    path = CANDLE_INTERVAL_MAP.get(interval)
    count = max(1, min(int(count), 200))

    if not market or not path:
        return _fallback_candles(coin, interval, count)

    try:
        resp = requests.get(
            f"{settings.upbit_candles_url}/{path}",
            params={"market": market, "count": count},
            timeout=settings.market_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        candles = []
        for item in reversed(data):  # 업비트는 최신순 → 오래된순으로 뒤집음
            candles.append(
                {
                    "time": item.get("candle_date_time_kst")
                    or item.get("candle_date_time_utc"),
                    "open": float(item["opening_price"]),
                    "high": float(item["high_price"]),
                    "low": float(item["low_price"]),
                    "close": float(item["trade_price"]),
                    "volume": float(item.get("candle_acc_trade_volume", 0)),
                }
            )
        return candles
    except Exception as exc:  # 네트워크/파싱 오류 → 폴백
        logger.warning("업비트 캔들 조회 실패(%s). 폴백 캔들을 사용합니다.", exc)
        return _fallback_candles(coin, interval, count)


def _fallback_candles(coin: str, interval: str, count: int) -> list[dict]:
    """폴백 캔들: 현재가 기준 가벼운 랜덤워크로 자연스러운 시세 흐름을 만든다."""
    base = FALLBACK.get(coin, {"price": 1000})["price"]
    step_min = _INTERVAL_MINUTES.get(interval, 60)
    rng = random.Random(hash(coin) & 0xFFFFFFFF)  # 코인별 고정 시드(재조회 시 안정적)
    now = datetime.now(timezone.utc)

    # 종가 시퀀스 생성 후 마지막 값을 현재가에 맞춤
    closes = []
    p = base * 0.97
    for _ in range(count):
        p *= 1 + rng.uniform(-0.015, 0.018)
        closes.append(p)
    scale = base / closes[-1] if closes[-1] else 1.0
    closes = [c * scale for c in closes]

    candles = []
    for i, close in enumerate(closes):
        o = closes[i - 1] if i > 0 else close * (1 + rng.uniform(-0.01, 0.01))
        hi = max(o, close) * (1 + rng.uniform(0, 0.01))
        lo = min(o, close) * (1 - rng.uniform(0, 0.01))
        t = (now - timedelta(minutes=step_min * (count - 1 - i))).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        candles.append(
            {
                "time": t,
                "open": round(o, 2),
                "high": round(hi, 2),
                "low": round(lo, 2),
                "close": round(close, 2),
                "volume": round(rng.uniform(1, 50), 3),
            }
        )
    return candles
