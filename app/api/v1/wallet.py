from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, require_idempotency_key
from app.models.common import LedgerEntry, Wallet, WalletTransaction
from app.models.user import User
from app.services.storage import get_db

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("")
async def get_wallet(current_user: User = Depends(get_current_user)) -> Wallet:
    db = get_db()
    return db.get_or_create_wallet(current_user.id)


@router.post("/credit")
async def credit_wallet(
    amount: float,
    note: str | None = None,
    idempotency_key: str = Depends(require_idempotency_key),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    db = get_db()
    if idempotency_key in db.idempotency_keys:
        return {"detail": "Already processed"}
    txn = WalletTransaction(user_id=current_user.id, type="credit", amount=amount, note=note)
    db.record_wallet_transaction(txn)
    db.idempotency_keys[idempotency_key] = txn.id
    entry = LedgerEntry(
        user_id=current_user.id,
        date=datetime.utcnow(),
        ref=txn.id,
        type="credit",
        credit=amount,
        debit=0.0,
        balance=db.wallets[current_user.id].balance,
        note=note,
    )
    db.add_ledger_entry(entry)
    return {"detail": "Wallet credited", "transaction_id": txn.id}


@router.post("/debit")
async def debit_wallet(
    amount: float,
    note: str | None = None,
    idempotency_key: str = Depends(require_idempotency_key),
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    db = get_db()
    if idempotency_key in db.idempotency_keys:
        return {"detail": "Already processed"}
    wallet = db.get_or_create_wallet(current_user.id)
    if wallet.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    txn = WalletTransaction(user_id=current_user.id, type="debit", amount=amount, note=note)
    db.record_wallet_transaction(txn)
    db.idempotency_keys[idempotency_key] = txn.id
    entry = LedgerEntry(
        user_id=current_user.id,
        date=datetime.utcnow(),
        ref=txn.id,
        type="debit",
        credit=0.0,
        debit=amount,
        balance=db.wallets[current_user.id].balance,
        note=note,
    )
    db.add_ledger_entry(entry)
    return {"detail": "Wallet debited", "transaction_id": txn.id}


@router.get("/transactions")
async def list_transactions(current_user: User = Depends(get_current_user)) -> List[WalletTransaction]:
    db = get_db()
    return [txn for txn in db.wallet_transactions.values() if txn.user_id == current_user.id]
