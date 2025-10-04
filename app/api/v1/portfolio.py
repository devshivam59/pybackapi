from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.common import Position
from app.models.user import User
from app.services.storage import get_db

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/holdings")
async def list_holdings(current_user: User = Depends(get_current_user)) -> List[Dict[str, object]]:
    db = get_db()
    holdings = []
    for position in db.positions.values():
        if position.user_id == current_user.id and position.side == "LONG":
            pnl = 5.0 * position.qty
            holdings.append({
                "instrument_id": position.instrument_id,
                "qty": position.qty,
                "avg_price": position.avg_price,
                "last_price": position.avg_price + 5,
                "pnl_abs": pnl,
                "pnl_pct": (pnl / (position.avg_price * position.qty)) * 100 if position.avg_price else 0,
            })
    return holdings


@router.get("/positions")
async def list_positions(current_user: User = Depends(get_current_user)) -> List[Dict[str, object]]:
    db = get_db()
    positions = []
    for position in db.positions.values():
        if position.user_id == current_user.id:
            positions.append({
                "instrument_id": position.instrument_id,
                "side": position.side,
                "qty": position.qty,
                "avg_price": position.avg_price,
                "mtm": 0.0,
                "realized_pnl": position.realized_pnl,
                "u_pnl": 0.0,
                "product": "CNC",
                "day_buy": 0,
                "day_sell": 0,
            })
    return positions


@router.get("/pnl/daily")
async def daily_pnl(current_user: User = Depends(get_current_user)) -> List[Dict[str, object]]:
    today = datetime.utcnow().date()
    return [
        {
            "date": (today - timedelta(days=idx)).isoformat(),
            "pnl": 100.0 - idx * 10,
        }
        for idx in range(5)
    ]


@router.get("/trades")
async def list_trades(current_user: User = Depends(get_current_user)) -> List[Dict[str, object]]:
    db = get_db()
    trades = []
    for trade in db.trades.values():
        if trade.user_id == current_user.id:
            trades.append(trade.dict())
    return trades
