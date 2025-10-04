from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(tags=["system"])


@router.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/config")
async def get_config(_: User = Depends(get_current_user)) -> Dict[str, str]:
    return {"banner": "Welcome to the trading API"}


@router.get("/markets/calendar")
async def market_calendar(_: User = Depends(get_current_user)) -> Dict[str, str]:
    return {"next_open": datetime.utcnow().date().isoformat(), "market": "NSE"}
