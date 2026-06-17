"""설정(업비트 API 키) 엔드포인트 (인증 필요)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import ApiKeyRequest, ApiKeyStatusResponse, MessageResponse
from ..services import settings_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/api-key", response_model=ApiKeyStatusResponse)
def api_key_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ApiKeyStatusResponse(**settings_service.get_api_key_status(db, user))


@router.post("/api-key", response_model=MessageResponse)
def save_api_key(
    payload: ApiKeyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings_service.save_api_key(db, user, payload.access_key, payload.secret_key)
    return MessageResponse(success=True, message="API 키가 저장되었습니다.")
