"""인증 관련 엔드포인트."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from ..services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    auth_service.register_user(db, payload.email, payload.password)
    return MessageResponse(success=True, message="계정 생성이 완료되었습니다.")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user, access, refresh = auth_service.login_user(db, payload.email, payload.password)
    return TokenResponse(access_token=access, refresh_token=refresh, email=user.email)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    access = auth_service.refresh_access_token(db, payload.refresh_token)
    return AccessTokenResponse(access_token=access)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    auth_service.logout(db, payload.refresh_token)
    return MessageResponse(success=True, message="로그아웃되었습니다.")
