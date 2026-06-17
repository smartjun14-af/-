"""
지갑(가상 원화) 비즈니스 로직: 잔고 조회 / 입금 / 출금 / 거래내역.
입금·출금은 잔고 변경과 거래내역 기록을 한 트랜잭션으로 처리합니다.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from ..exceptions import InsufficientBalanceError, InvalidAmountError
from ..models import Balance, Transaction, User


def get_or_create_balance(db: Session, user: User) -> Balance:
    bal = db.query(Balance).filter(Balance.user_id == user.id).first()
    if not bal:
        bal = Balance(user_id=user.id, krw_balance=0, frozen_balance=0)
        db.add(bal)
        db.commit()
        db.refresh(bal)
    return bal


def deposit(db: Session, user: User, amount: int) -> tuple[Balance, Transaction]:
    if amount <= 0:
        raise InvalidAmountError()

    bal = get_or_create_balance(db, user)
    bal.krw_balance = bal.krw_balance + Decimal(amount)
    tx = Transaction(
        user_id=user.id,
        transaction_type="DEPOSIT",
        amount=Decimal(amount),
        balance_after=bal.krw_balance,
    )
    db.add(tx)
    db.commit()
    db.refresh(bal)
    db.refresh(tx)
    return bal, tx


def withdraw(db: Session, user: User, amount: int) -> tuple[Balance, Transaction]:
    if amount <= 0:
        raise InvalidAmountError()

    bal = get_or_create_balance(db, user)
    if Decimal(amount) > bal.krw_balance:
        raise InsufficientBalanceError()

    bal.krw_balance = bal.krw_balance - Decimal(amount)
    tx = Transaction(
        user_id=user.id,
        transaction_type="WITHDRAW",
        amount=Decimal(amount),
        balance_after=bal.krw_balance,
    )
    db.add(tx)
    db.commit()
    db.refresh(bal)
    db.refresh(tx)
    return bal, tx


def recent_transactions(db: Session, user: User, limit: int = 5) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .limit(limit)
        .all()
    )


def list_transactions(
    db: Session, user: User, tx_type: str | None = None
) -> list[Transaction]:
    q = db.query(Transaction).filter(Transaction.user_id == user.id)
    if tx_type in ("DEPOSIT", "WITHDRAW"):
        q = q.filter(Transaction.transaction_type == tx_type)
    return q.order_by(Transaction.created_at.desc(), Transaction.id.desc()).all()
