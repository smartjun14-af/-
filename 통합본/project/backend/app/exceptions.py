"""
도메인 커스텀 예외 + 전역 예외 핸들러.
"""
import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("coin")


class AppException(Exception):

    status_code = status.HTTP_400_BAD_REQUEST
    code = "BAD_REQUEST"
    message = "잘못된 요청입니다."

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)


class EmailAlreadyExistsError(AppException):
    status_code = status.HTTP_409_CONFLICT
    code = "EMAIL_ALREADY_EXISTS"
    message = "이미 가입된 이메일입니다."


class InvalidCredentialsError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "INVALID_CREDENTIALS"
    message = "이메일 또는 비밀번호가 올바르지 않습니다."


class InactiveUserError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "INACTIVE_USER"
    message = "비활성화된 계정입니다."


class InvalidTokenError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "INVALID_TOKEN"
    message = "인증 정보가 유효하지 않습니다. 다시 로그인해주세요."


class UserNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "USER_NOT_FOUND"
    message = "사용자를 찾을 수 없습니다."


class InsufficientBalanceError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "INSUFFICIENT_BALANCE"
    message = "출금 금액이 보유 잔고를 초과합니다."


class InvalidAmountError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "INVALID_AMOUNT"
    message = "올바른 금액을 입력해주세요. (1원 이상)"


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppException)
    async def _app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        raw_msg = first.get("msg", "입력값이 올바르지 않습니다.")
        msg = f"입력값 오류({field}): {raw_msg}" if field else raw_msg
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": {"code": "VALIDATION_ERROR", "message": msg, "errors": errors}},
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": {"code": "INTERNAL_ERROR", "message": "서버 내부 오류가 발생했습니다."}},
        )
