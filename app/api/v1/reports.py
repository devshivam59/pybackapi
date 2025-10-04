from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/pnl")
async def get_pnl(
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    breakdown: str = Query(default="day"),
    _: User = Depends(get_current_user),
) -> Dict[str, List[Dict[str, float]]]:
    to_dt = to_date or datetime.utcnow()
    from_dt = from_date or to_dt - timedelta(days=5)
    data = []
    current = from_dt
    while current <= to_dt:
        data.append({"key": current.isoformat(), "pnl": 100.0})
        current += timedelta(days=1)
    return {"breakdown": breakdown, "data": data}


@router.get("/taxes")
async def get_taxes(_: User = Depends(get_current_user)) -> Dict[str, float]:
    return {"tax_payable": 0.0}


@router.get("/contract-notes")
async def list_contract_notes(_: User = Depends(get_current_user)) -> List[Dict[str, str]]:
    return [{"date": datetime.utcnow().date().isoformat(), "url": "https://example.com/contract-note.pdf"}]


@router.get("/export")
async def export_reports(_: User = Depends(get_current_user)) -> Dict[str, str]:
    return {"detail": "Report generation scheduled", "download_url": "https://example.com/export.csv"}
