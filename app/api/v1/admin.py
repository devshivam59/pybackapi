from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import require_admin
from app.models.common import InstrumentImport, Order, Position
from app.models.user import User
from app.services.instrument_store import instrument_store
from app.services.kite import kite_service
from app.services.storage import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


class KiteTokenPayload(BaseModel):
    api_key: str
    access_token: str
    valid_till: Optional[datetime] = None


class KiteSessionPayload(BaseModel):
    request_token: str


class DashboardImport(BaseModel):
    id: str
    source: str
    status: str
    rows_in: int
    rows_ok: int
    rows_err: int
    started_at: datetime
    finished_at: Optional[datetime]


class DashboardTotals(BaseModel):
    users: int
    instruments: int
    watchlists: int
    watchlist_items: int
    orders: int
    positions: int


class DashboardKiteStatus(BaseModel):
    configured: bool
    api_key_last4: Optional[str] = None
    access_token_last4: Optional[str] = None
    valid_till: Optional[str] = None
    updated_at: Optional[str] = None
    request_token: Optional[str] = None
    request_token_at: Optional[str] = None
    base_url: Optional[str] = None


class DashboardSummary(BaseModel):
    totals: DashboardTotals
    kite_status: DashboardKiteStatus
    latest_import: Optional[DashboardImport] = None


@router.get("/orders")
async def list_orders(
    _: User = Depends(require_admin),
    status: Optional[str] = Query(default=None),
) -> List[Order]:
    db = get_db()
    orders = list(db.orders.values())
    if status:
        orders = [order for order in orders if order.status == status]
    return orders


@router.post("/orders/{order_id}/override")
async def override_order(
    order_id: str,
    status: str,
    note: Optional[str] = None,
    _: User = Depends(require_admin),
) -> Dict[str, str]:
    db = get_db()
    order = db.orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    order.status = status
    return {"detail": "Order overridden", "note": note or ""}


@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(_: User = Depends(require_admin)) -> DashboardSummary:
    db = get_db()
    totals = DashboardTotals(
        users=len(db.users),
        instruments=instrument_store.count_instruments(),
        watchlists=len(db.watchlists),
        watchlist_items=len(db.watchlist_items),
        orders=len(db.orders),
        positions=len(db.positions),
    )

    kite_raw = kite_service.status()
    kite_status = DashboardKiteStatus(**kite_raw)

    latest_import: Optional[InstrumentImport] = None
    imports = instrument_store.list_imports()
    if imports:
        latest_import = imports[0]

    import_snapshot = (
        DashboardImport(
            id=latest_import.id,
            source=latest_import.source,
            status=latest_import.status,
            rows_in=latest_import.rows_in,
            rows_ok=latest_import.rows_ok,
            rows_err=latest_import.rows_err,
            started_at=latest_import.started_at,
            finished_at=latest_import.finished_at,
        )
        if latest_import
        else None
    )

    return DashboardSummary(totals=totals, kite_status=kite_status, latest_import=import_snapshot)


@router.get("/positions")
async def list_positions(
    user_id: Optional[str] = Query(default=None),
    _: User = Depends(require_admin),
) -> List[Position]:
    db = get_db()
    positions = list(db.positions.values())
    if user_id:
        positions = [position for position in positions if position.user_id == user_id]
    return positions


@router.post("/positions")
async def create_position(
    user_id: str,
    instrument_id: str,
    side: str,
    qty: int,
    avg_price: float,
    as_of_date: str,
    _: User = Depends(require_admin),
) -> Position:
    db = get_db()
    position = Position(
        user_id=user_id,
        instrument_id=instrument_id,
        side=side,
        qty=qty,
        avg_price=avg_price,
    )
    position.as_of_date = datetime.fromisoformat(as_of_date)
    db.positions[position.id] = position
    return position


@router.put("/positions/{position_id}")
async def update_position(
    position_id: str,
    qty: Optional[int] = None,
    avg_price: Optional[float] = None,
    reason: Optional[str] = None,
    _: User = Depends(require_admin),
) -> Position:
    db = get_db()
    position = db.positions.get(position_id)
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    if qty is not None:
        position.qty = qty
    if avg_price is not None:
        position.avg_price = avg_price
    return position


@router.delete("/positions/{position_id}")
async def delete_position(position_id: str, _: User = Depends(require_admin)) -> Dict[str, str]:
    db = get_db()
    if position_id not in db.positions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    db.positions.pop(position_id)
    return {"detail": "Position removed"}


@router.get("/users")
async def list_users(
    _: User = Depends(require_admin),
    search: Optional[str] = Query(default=None),
) -> List[User]:
    db = get_db()
    users = list(db.users.values())
    if search:
        users = [user for user in users if search.lower() in user.email.lower()]
    return users


@router.get("/users/{user_id}")
async def get_user(user_id: str, _: User = Depends(require_admin)) -> User:
    db = get_db()
    user = db.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/users/{user_id}/approve")
async def approve_user(
    user_id: str,
    approved: bool,
    note: Optional[str] = None,
    _: User = Depends(require_admin),
) -> Dict[str, str]:
    db = get_db()
    user = db.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.approved = approved  # type: ignore[attr-defined]
    return {"detail": "User updated", "note": note or ""}


@router.put("/users/{user_id}/roles")
async def update_user_roles(
    user_id: str,
    roles: List[str],
    _: User = Depends(require_admin),
) -> Dict[str, List[str]]:
    db = get_db()
    user = db.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.roles = roles
    return {"roles": user.roles}


@router.get("/brokers/zerodha/token")
async def get_zerodha_token(_: User = Depends(require_admin)) -> Dict[str, Optional[str]]:
    return kite_service.status()


@router.post("/brokers/zerodha/token")
async def set_zerodha_token(
    payload: KiteTokenPayload,
    _: User = Depends(require_admin),
) -> Dict[str, str]:
    if not payload.api_key.strip() or not payload.access_token.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key and access token are required")
    kite_service.set_credentials(
        api_key=payload.api_key,
        access_token=payload.access_token,
        valid_till=payload.valid_till,
    )
    return {"detail": "Kite credentials updated"}


@router.delete("/brokers/zerodha/token")
async def clear_zerodha_token(_: User = Depends(require_admin)) -> Dict[str, str]:
    kite_service.clear_credentials()
    return {"detail": "Kite credentials cleared"}


@router.post("/brokers/zerodha/session/complete")
async def complete_zerodha_session(
    payload: KiteSessionPayload,
    _: User = Depends(require_admin),
) -> Dict[str, str]:
    kite_service.record_request_token(payload.request_token)
    return {"detail": "Request token recorded"}


@router.post("/brokers/zerodha/test")
async def test_zerodha(_: User = Depends(require_admin)) -> Dict[str, str]:
    ok, message = await kite_service.ping()
    if not ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message)
    return {"detail": message}
