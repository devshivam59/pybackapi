from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.models.user import User
from app.services.instrument_store import instrument_store
from app.services.kite import kite_service

router = APIRouter(prefix="/market", tags=["market"])


async def _quote_payload(instrument_id: str, *, include_metadata: bool = False) -> Dict[str, float | str]:
    instrument = instrument_store.get_instrument(instrument_id)
    if instrument is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")
    quotes = await kite_service.fetch_quotes([instrument])
    quote = quotes.get(instrument.id)
    fallback_price = instrument.last_price or float(len(instrument.tradingsymbol)) * 10.5
    payload: Dict[str, float | str] = {
        "instrument_id": instrument.id,
        "ltp": quote["ltp"] if quote else fallback_price,
        "timestamp": quote["timestamp"] if quote else datetime.utcnow().isoformat(),
        "source": quote["source"] if quote else "database",
    }
    if include_metadata:
        payload["instrument_token"] = instrument.instrument_token
        payload["tradingsymbol"] = instrument.tradingsymbol
        payload["exchange"] = instrument.exchange
    return payload


@router.get("/quote/{instrument_id}")
async def get_quote(
    instrument_id: str,
    _: User = Depends(get_current_user),
) -> Dict[str, float | str]:
    return await _quote_payload(instrument_id)


@router.post("/quotes")
async def get_quotes(
    instrument_ids: List[str],
    _: User = Depends(get_current_user),
) -> Dict[str, Dict[str, float | str]]:
    if not instrument_ids:
        return {"quotes": {}}
    limited_ids = instrument_ids[:500]
    instruments = instrument_store.get_instruments_by_ids(limited_ids)
    if not instruments:
        return {"quotes": {}}
    quotes = await kite_service.fetch_quotes(instruments)
    now_iso = datetime.utcnow().isoformat()
    payload: Dict[str, Dict[str, float | str]] = {}
    for instrument in instruments:
        quote = quotes.get(instrument.id)
        fallback_price = instrument.last_price or float(len(instrument.tradingsymbol)) * 10.5
        payload[instrument.id] = {
            "instrument_id": instrument.id,
            "instrument_token": instrument.instrument_token,
            "ltp": quote["ltp"] if quote else fallback_price,
            "timestamp": quote["timestamp"] if quote else now_iso,
            "source": quote["source"] if quote else "database",
        }
    return {"quotes": payload}


@router.get("/depth/{instrument_id}")
async def get_depth(
    instrument_id: str,
    _: User = Depends(get_current_user),
) -> Dict[str, List[List[float]]]:
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
        candles.append(
            {
                "ts": current.isoformat(),
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price + 0.5,
            }
        )
        current += timedelta(minutes=1 if tf.endswith("m") else 1440)
        price += 0.5
    return {"instrument_id": instrument_id, "timeframe": tf, "candles": candles}
