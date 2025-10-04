from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user
from app.models.user import User
from app.services.instrument_store import instrument_store

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/quote/{instrument_id}")
async def get_quote(instrument_id: str, _: User = Depends(get_current_user)) -> Dict[str, float]:
    instrument = instrument_store.get_instrument(instrument_id)
    if instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    price = instrument.last_price or float(len(instrument.tradingsymbol)) * 10.5
    return {"instrument_id": instrument_id, "ltp": price, "timestamp": datetime.utcnow().isoformat()}


@router.post("/quotes")
async def get_quotes(
    instrument_ids: List[str],
    _: User = Depends(get_current_user),
) -> Dict[str, Dict[str, float]]:
    quotes = {}
    for instrument_id in instrument_ids[:500]:
        quotes[instrument_id] = {"ltp": float(len(instrument_id)) * 5.2}
    return {"quotes": quotes}


@router.get("/depth/{instrument_id}")
async def get_depth(instrument_id: str, _: User = Depends(get_current_user)) -> Dict[str, List[List[float]]]:
    bids = [[100.0, 50], [99.5, 75], [99.0, 120]]
    asks = [[100.5, 40], [101.0, 60], [101.5, 90]]
    return {"instrument_id": instrument_id, "bids": bids, "asks": asks}


@router.get("/ohlc/{instrument_id}")
async def get_ohlc(
    instrument_id: str,
    tf: str = Query(default="1d"),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    _: User = Depends(get_current_user),
) -> Dict[str, List[Dict[str, float]]]:
    end = to or datetime.utcnow()
    start = from_ or end - timedelta(days=5)
    candles: List[Dict[str, float]] = []
    current = start
    price = 100.0
    while current <= end:
        candles.append({
            "ts": current.isoformat(),
            "open": price,
            "high": price + 1,
            "low": price - 1,
            "close": price + 0.5,
        })
        current += timedelta(minutes=1 if tf.endswith("m") else 1440)
        price += 0.5
    return {"instrument_id": instrument_id, "timeframe": tf, "candles": candles}
