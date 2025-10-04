from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, require_admin
from app.models.common import LedgerEntry
from app.models.user import User
from app.services.storage import get_db

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("")
async def list_ledger(current_user: User = Depends(get_current_user)) -> List[LedgerEntry]:
    db = get_db()
    return [entry for entry in db.ledger_entries.values() if entry.user_id == current_user.id]


@router.post("/adjustment")
async def create_adjustment(
    user_id: str,
    entry_type: str,
    amount: float,
    note: str | None = None,
    _: User = Depends(require_admin),
) -> LedgerEntry:
    if entry_type not in {"debit", "credit"}:
        raise HTTPException(status_code=400, detail="Invalid entry type")
    db = get_db()
    entry = LedgerEntry(
        user_id=user_id,
        date=datetime.utcnow(),
        ref=f"adj_{len(db.ledger_entries) + 1}",
        type=entry_type,
        debit=amount if entry_type == "debit" else 0.0,
        credit=amount if entry_type == "credit" else 0.0,
        balance=db.get_or_create_wallet(user_id).balance,
        note=note,
    )
    db.add_ledger_entry(entry)
    return entry
