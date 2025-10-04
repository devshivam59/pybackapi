from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import require_admin
from app.models.common import InstrumentSource
from app.models.user import User
from app.services.storage import get_db

router = APIRouter(prefix="/instruments/sources", tags=["automations"])


@router.post("/{source_id}/run-now")
async def run_source_now(source_id: str, _: User = Depends(require_admin)) -> Dict[str, str]:
    db = get_db()
    source = db.instrument_sources.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    source.last_run_at = datetime.utcnow()
    source.last_status = "triggered"
    return {"detail": "Run started"}


@router.put("/{source_id}")
async def update_source(
    source_id: str,
    enabled: bool | None = None,
    schedule: str | None = None,
    _: User = Depends(require_admin),
) -> InstrumentSource:
    db = get_db()
    source = db.instrument_sources.get(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    if enabled is not None:
        source.enabled = enabled
    if schedule is not None:
        source.schedule_cron = schedule
    return source
