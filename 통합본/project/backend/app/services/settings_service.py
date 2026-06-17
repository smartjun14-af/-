"""
설정 화면의 업비트 API 키 저장/조회.
키는 AES-256-GCM으로 암호화하여 DB에 보관하고, 조회 시 마스킹된 값만 반환합니다.
"""
from sqlalchemy.orm import Session

from ..models import ApiKey, User
from ..security import decrypt_secret, encrypt_secret


def save_api_key(db: Session, user: User, access_key: str, secret_key: str) -> ApiKey:
    rec = db.query(ApiKey).filter(ApiKey.user_id == user.id).first()
    if rec:
        rec.access_key_enc = encrypt_secret(access_key)
        rec.secret_key_enc = encrypt_secret(secret_key)
    else:
        rec = ApiKey(
            user_id=user.id,
            access_key_enc=encrypt_secret(access_key),
            secret_key_enc=encrypt_secret(secret_key),
        )
        db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def _mask(value: str) -> str:
    if len(value) <= 8:
        return "•" * len(value)
    return value[:4] + "•" * (len(value) - 8) + value[-4:]


def get_api_key_status(db: Session, user: User) -> dict:
    rec = db.query(ApiKey).filter(ApiKey.user_id == user.id).first()
    if not rec:
        return {"registered": False, "access_key_masked": None}
    try:
        masked = _mask(decrypt_secret(rec.access_key_enc))
    except Exception:
        masked = "••••••••"
    return {"registered": True, "access_key_masked": masked}
