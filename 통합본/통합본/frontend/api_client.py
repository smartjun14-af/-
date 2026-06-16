"""
백엔드(FastAPI) 통신 클라이언트.

- 모든 호출은 이 모듈을 통해 이루어진다.
- 백엔드의 통일된 오류 형식 {"detail": {"code", "message"}} 를 파싱해
  ApiError 로 변환한다.
- 서버에 아예 연결되지 않는 경우(백엔드 미실행 등)에는 사용자가 이해할 수 있는
  한국어 메시지를 담은 ApiError 를 발생시킨다.

환경변수 BACKEND_URL 로 백엔드 주소를 바꿀 수 있다. (기본: http://127.0.0.1:8000)
"""
import os

import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

# 네트워크 타임아웃(초). 백엔드가 응답하지 않을 때 무한 대기하지 않도록 한다.
TIMEOUT = float(os.environ.get("BACKEND_TIMEOUT", "10"))


class ApiError(Exception):
    """백엔드 호출 실패를 표현하는 예외.

    status:  HTTP 상태 코드 (연결 자체 실패 시 None)
    code:    백엔드가 내려준 오류 코드 (예: INSUFFICIENT_BALANCE)
    message: 사용자에게 보여줄 한국어 메시지
    """

    def __init__(self, message: str, status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def _request(method: str, path: str, token: str | None = None, json: dict | None = None) -> dict | list:
    url = f"{BACKEND_URL}{path}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.request(method, url, json=json, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.ConnectionError:
        raise ApiError(
            "서버에 연결할 수 없습니다. 백엔드(8000번 포트)가 실행 중인지 확인해주세요.",
            status=None,
            code="CONNECTION_ERROR",
        )
    except requests.exceptions.Timeout:
        raise ApiError(
            "서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.",
            status=None,
            code="TIMEOUT",
        )
    except requests.exceptions.RequestException:
        raise ApiError(
            "요청 처리 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            status=None,
            code="NETWORK_ERROR",
        )

    # 성공 (2xx)
    if 200 <= resp.status_code < 300:
        if resp.status_code == 204 or not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {}

    # 실패 → 백엔드의 통일된 오류 형식에서 code/message 추출
    code = None
    message = None
    try:
        body = resp.json()
        detail = body.get("detail")
        if isinstance(detail, dict):
            code = detail.get("code")
            message = detail.get("message")
        elif isinstance(detail, str):
            message = detail
    except ValueError:
        pass

    if not message:
        message = f"요청이 실패했습니다. (HTTP {resp.status_code})"

    raise ApiError(message, status=resp.status_code, code=code)


# =========================
# 인증
# =========================
def register(email: str, password: str) -> dict:
    return _request("POST", "/api/auth/register", json={"email": email, "password": password})


def login(email: str, password: str) -> dict:
    """성공 시 {'access_token','refresh_token','token_type','email'} 반환."""
    return _request("POST", "/api/auth/login", json={"email": email, "password": password})


def refresh(refresh_token: str) -> dict:
    return _request("POST", "/api/auth/refresh", json={"refresh_token": refresh_token})


def logout(refresh_token: str) -> dict:
    return _request("POST", "/api/auth/logout", json={"refresh_token": refresh_token})


# =========================
# 대시보드 / 지갑
# =========================
def get_dashboard(token: str) -> dict:
    """{'summary': {...}, 'coins': [...], 'recent_transactions': [...]}"""
    return _request("GET", "/api/dashboard", token=token)


def get_candles(token: str, coin: str = "BTC", interval: str = "day", count: int = 30) -> dict:
    """차트용 과거 시세(캔들). {'coin','interval','candles':[{time,open,high,low,close,volume}]}"""
    path = f"/api/candles?coin={coin}&interval={interval}&count={count}"
    return _request("GET", path, token=token)


def get_balance(token: str) -> dict:
    """{'krw_balance': float, 'frozen_balance': float}"""
    return _request("GET", "/api/balance", token=token)


def deposit(token: str, amount: int) -> dict:
    return _request("POST", "/api/deposit", token=token, json={"amount": amount})


def withdraw(token: str, amount: int) -> dict:
    return _request("POST", "/api/withdraw", token=token, json={"amount": amount})


def get_transactions(token: str, tx_type: str | None = None) -> list:
    """입출금 거래 내역 목록(최신순). tx_type: 'DEPOSIT' | 'WITHDRAW' | None(전체)"""
    path = "/api/transactions"
    if tx_type:
        path += f"?type={tx_type}"
    return _request("GET", path, token=token)


# =========================
# 설정 (업비트 API 키)
# =========================
def get_api_key_status(token: str) -> dict:
    """{'registered': bool, 'access_key_masked': str | None}"""
    return _request("GET", "/api/settings/api-key", token=token)


def save_api_key(token: str, access_key: str, secret_key: str) -> dict:
    return _request(
        "POST",
        "/api/settings/api-key",
        token=token,
        json={"access_key": access_key, "secret_key": secret_key},
    )
