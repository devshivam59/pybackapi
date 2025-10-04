from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.common import Watchlist, WatchlistItem
from app.models.user import User
from app.services.instrument_store import instrument_store
from app.services.kite import kite_service
from app.services.storage import get_db

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


class WatchlistCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class WatchlistUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    reorder: Optional[List[str]] = None


class WatchlistItemCreateRequest(BaseModel):
    instrument_id: str


def _assert_watchlist_owner(watchlist: Watchlist, user: User) -> None:
    if watchlist.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")


@router.get("")
async def list_watchlists(current_user: User = Depends(get_current_user)) -> List[Watchlist]:
    db = get_db()
    return [wl for wl in db.watchlists.values() if wl.user_id == current_user.id]


@router.post("")
async def create_watchlist(
    payload: WatchlistCreateRequest,
    current_user: User = Depends(get_current_user),
) -> Watchlist:
    db = get_db()
    watchlist = Watchlist(user_id=current_user.id, name=payload.name.strip())
    db.watchlists[watchlist.id] = watchlist
    return watchlist


@router.put("/{watchlist_id}")
async def update_watchlist(
    watchlist_id: str,
    payload: WatchlistUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> Watchlist:
    db = get_db()
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    _assert_watchlist_owner(watchlist, current_user)
    if payload.name:
        watchlist.name = payload.name.strip()
    if payload.reorder:
        order_lookup = {item_id: index for index, item_id in enumerate(payload.reorder)}
        for item in db.watchlist_items.values():
            if item.watchlist_id == watchlist_id and item.id in order_lookup:
                item.sort_order = order_lookup[item.id]
    return watchlist


@router.delete("/{watchlist_id}")
async def delete_watchlist(
    watchlist_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    db = get_db()
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    _assert_watchlist_owner(watchlist, current_user)
    db.watchlists.pop(watchlist_id)
    for item_id in list(db.watchlist_items):
        if db.watchlist_items[item_id].watchlist_id == watchlist_id:
            db.watchlist_items.pop(item_id)
    return {"detail": "Watchlist deleted"}


@router.post("/{watchlist_id}/items")
async def add_watchlist_item(
    watchlist_id: str,
    payload: WatchlistItemCreateRequest,
    current_user: User = Depends(get_current_user),
) -> WatchlistItem:
    db = get_db()
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    _assert_watchlist_owner(watchlist, current_user)
    instrument = instrument_store.get_instrument(payload.instrument_id)
    if instrument is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")
    existing = [
        item
        for item in db.watchlist_items.values()
        if item.watchlist_id == watchlist_id and item.instrument_id == payload.instrument_id
    ]
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Instrument already in watchlist")
    order = len([item for item in db.watchlist_items.values() if item.watchlist_id == watchlist_id])
    item = WatchlistItem(watchlist_id=watchlist_id, instrument_id=payload.instrument_id, sort_order=order)
    db.watchlist_items[item.id] = item
    return item


@router.delete("/{watchlist_id}/items/{item_id}")
async def delete_watchlist_item(
    watchlist_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    db = get_db()
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    _assert_watchlist_owner(watchlist, current_user)
    item = db.watchlist_items.get(item_id)
    if item is None or item.watchlist_id != watchlist_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db.watchlist_items.pop(item_id)
    return {"detail": "Item removed"}


@router.post("/{watchlist_id}/items/{item_id}/order")
async def shortcut_order(
    watchlist_id: str,
    item_id: str,
    order_details: Dict[str, str],
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    db = get_db()
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    _assert_watchlist_owner(watchlist, current_user)
    item = db.watchlist_items.get(item_id)
    if item is None or item.watchlist_id != watchlist_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return {"detail": "Order placement queued", "instrument_id": item.instrument_id, **order_details}


@router.get("/{watchlist_id}/items")
async def list_watchlist_items(
    watchlist_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    db = get_db()
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    _assert_watchlist_owner(watchlist, current_user)
    items = sorted(
        (item for item in db.watchlist_items.values() if item.watchlist_id == watchlist_id),
        key=lambda entry: entry.sort_order,
    )
    instrument_ids = [item.instrument_id for item in items]
    instruments = instrument_store.get_instruments_by_ids(instrument_ids)
    instrument_map = {instrument.id: instrument for instrument in instruments}
    quotes = await kite_service.fetch_quotes(instruments)
    now_iso = datetime.utcnow().isoformat()
    response_items: List[Dict[str, Any]] = []
    for item in items:
        instrument = instrument_map.get(item.instrument_id)
        if instrument is None:
            response_items.append(
                {
                    "item_id": item.id,
                    "instrument_id": item.instrument_id,
                    "missing": True,
                }
            )
            continue
        quote = quotes.get(instrument.id)
        price = quote["ltp"] if quote else instrument.last_price or 0.0
        response_items.append(
            {
                "item_id": item.id,
                "instrument_id": instrument.id,
                "instrument_token": instrument.instrument_token,
                "tradingsymbol": instrument.tradingsymbol,
                "name": instrument.name,
                "exchange": instrument.exchange,
                "segment": instrument.segment,
                "instrument_type": instrument.instrument_type,
                "lot_size": instrument.lot_size,
                "tick_size": instrument.tick_size,
                "last_price": instrument.last_price,
                "live_price": price,
                "quote_source": quote["source"] if quote else "database",
                "quote_timestamp": quote["timestamp"] if quote else now_iso,
            }
        )
    return {
        "watchlist": watchlist,
        "items": response_items,
        "quotes_refreshed_at": now_iso,
        "kite_status": kite_service.status(),
    }
