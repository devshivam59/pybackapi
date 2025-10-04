from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.models.common import Watchlist, WatchlistItem
from app.models.user import User
from app.services.storage import get_db

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


@router.get("")
async def list_watchlists(current_user: User = Depends(get_current_user)) -> List[Watchlist]:
    db = get_db()
    return [wl for wl in db.watchlists.values() if wl.user_id == current_user.id]


@router.post("")
async def create_watchlist(name: str, current_user: User = Depends(get_current_user)) -> Watchlist:
    db = get_db()
    watchlist = Watchlist(user_id=current_user.id, name=name)
    db.watchlists[watchlist.id] = watchlist
    return watchlist


@router.put("/{watchlist_id}")
async def update_watchlist(
    watchlist_id: str,
    name: str | None = None,
    reorder: List[str] | None = None,
    current_user: User = Depends(get_current_user),
) -> Watchlist:
    db = get_db()
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None or watchlist.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    if name:
        watchlist.name = name
    if reorder:
        for index, item_id in enumerate(reorder):
            item = db.watchlist_items.get(item_id)
            if item and item.watchlist_id == watchlist_id:
                item.sort_order = index
    return watchlist


@router.delete("/{watchlist_id}")
async def delete_watchlist(watchlist_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    db = get_db()
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None or watchlist.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    db.watchlists.pop(watchlist_id)
    for item_id in list(db.watchlist_items):
        if db.watchlist_items[item_id].watchlist_id == watchlist_id:
            db.watchlist_items.pop(item_id)
    return {"detail": "Watchlist deleted"}


@router.post("/{watchlist_id}/items")
async def add_watchlist_item(
    watchlist_id: str,
    instrument_id: str,
    current_user: User = Depends(get_current_user),
) -> WatchlistItem:
    db = get_db()
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None or watchlist.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    order = len([item for item in db.watchlist_items.values() if item.watchlist_id == watchlist_id])
    item = WatchlistItem(watchlist_id=watchlist_id, instrument_id=instrument_id, sort_order=order)
    db.watchlist_items[item.id] = item
    return item


@router.delete("/{watchlist_id}/items/{item_id}")
async def delete_watchlist_item(
    watchlist_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    db = get_db()
    item = db.watchlist_items.get(item_id)
    if item is None or item.watchlist_id != watchlist_id:
        raise HTTPException(status_code=404, detail="Item not found")
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None or watchlist.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Watchlist not found")
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
    item = db.watchlist_items.get(item_id)
    if item is None or item.watchlist_id != watchlist_id:
        raise HTTPException(status_code=404, detail="Item not found")
    watchlist = db.watchlists.get(watchlist_id)
    if watchlist is None or watchlist.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return {"detail": "Order placement queued", "instrument_id": item.instrument_id, **order_details}
