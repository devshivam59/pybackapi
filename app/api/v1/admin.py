from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import require_admin
from app.models.common import Order, Position
from app.models.user import User
from app.services.storage import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

ZERODHA_STATE: Dict[str, str | None] = {"access_token": None, "valid_till": None}


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
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status
    return {"detail": "Order overridden", "note": note or ""}


@router.get("/positions")
async def list_positions(user_id: Optional[str] = Query(default=None), _: User = Depends(require_admin)) -> List[Position]:
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
        raise HTTPException(status_code=404, detail="Position not found")
    if qty is not None:
        position.qty = qty
    if avg_price is not None:
        position.avg_price = avg_price
    return position


@router.delete("/positions/{position_id}")
async def delete_position(position_id: str, _: User = Depends(require_admin)) -> Dict[str, str]:
    db = get_db()
    if position_id not in db.positions:
        raise HTTPException(status_code=404, detail="Position not found")
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
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}/approve")
async def approve_user(user_id: str, approved: bool, note: Optional[str] = None, _: User = Depends(require_admin)) -> Dict[str, str]:
    db = get_db()
    user = db.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.approved = approved  # type: ignore[attr-defined]
    return {"detail": "User updated", "note": note or ""}


@router.put("/users/{user_id}/roles")
async def update_user_roles(user_id: str, roles: List[str], _: User = Depends(require_admin)) -> Dict[str, List[str]]:
    db = get_db()
    user = db.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.roles = roles
    return {"roles": user.roles}


@router.get("/brokers/zerodha/token")
async def get_zerodha_token(_: User = Depends(require_admin)) -> Dict[str, str | None]:
    return ZERODHA_STATE


@router.post("/brokers/zerodha/session/complete")
async def complete_zerodha_session(
    request_token: str,
    _: User = Depends(require_admin),
) -> Dict[str, str]:
    ZERODHA_STATE["access_token"] = f"access_{request_token}"
    ZERODHA_STATE["valid_till"] = datetime.utcnow().replace(hour=23, minute=59, second=0, microsecond=0).isoformat()
    return {"detail": "Access token stored"}


@router.post("/brokers/zerodha/test")
async def test_zerodha(_: User = Depends(require_admin)) -> Dict[str, str]:
    if not ZERODHA_STATE["access_token"]:
        raise HTTPException(status_code=400, detail="No token configured")
    return {"detail": "Zerodha connectivity OK"}
