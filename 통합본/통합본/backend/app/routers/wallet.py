"""지갑(입출금/잔고) 엔드포인트 (인증 필요)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Balance, Transaction, User
from ..schemas import AmountRequest, BalanceResponse, TransactionResponse
from ..services import wallet_service

router = APIRouter(prefix="/api", tags=["wallet"])


def _balance_out(bal: Balance) -> BalanceResponse:
    return BalanceResponse(
        krw_balance=float(bal.krw_balance),
        frozen_balance=float(bal.frozen_balance),
    )


def _tx_out(t: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=t.id,
        transaction_type=t.transaction_type,
        amount=float(t.amount),
        balance_after=float(t.balance_after),
        created_at=t.created_at,
    )


@router.get("/balance", response_model=BalanceResponse)
def get_balance(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _balance_out(wallet_service.get_or_create_balance(db, user))


@router.post("/deposit", response_model=BalanceResponse)
def deposit(
    payload: AmountRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bal, _ = wallet_service.deposit(db, user, payload.amount)
    return _balance_out(bal)


@router.post("/withdraw", response_model=BalanceResponse)
def withdraw(
    payload: AmountRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bal, _ = wallet_service.withdraw(db, user, payload.amount)
    return _balance_out(bal)


@router.get("/transactions", response_model=list[TransactionResponse])
def transactions(
    type: str | None = Query(default=None, description="입금/출금/DEPOSIT/WITHDRAW"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tx_type = None
    if type in ("입금", "DEPOSIT"):
        tx_type = "DEPOSIT"
    elif type in ("출금", "WITHDRAW"):
        tx_type = "WITHDRAW"
    rows = wallet_service.list_transactions(db, user, tx_type)
    return [_tx_out(t) for t in rows]
