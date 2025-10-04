from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, require_idempotency_key
from app.models.common import Order, Trade
from app.models.user import User
from app.services.storage import get_db

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("")
async def create_order(
    instrument_id: str,
    side: str,
    qty: int,
    order_type: str,
    product: str,
    validity: str,
    price: float | None = None,
    trigger: float | None = None,
    disclosed_qty: int | None = None,
    idempotency_key: str = Depends(require_idempotency_key),
    current_user: User = Depends(get_current_user),
) -> Order:
    db = get_db()
    existing = db.idempotency_keys.get(idempotency_key)
    if existing:
        order = db.orders.get(existing)
        if order:
            return order
    order = Order(
        user_id=current_user.id,
        instrument_id=instrument_id,
        side=side,
        qty=qty,
        order_type=order_type,
        product=product,
        validity=validity,
        price=price,
        trigger=trigger,
        idempotency_key=idempotency_key,
    )
    db.orders[order.id] = order
    db.idempotency_keys[idempotency_key] = order.id
    return order


@router.get("")
async def list_orders(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
) -> List[Order]:
    db = get_db()
    orders = [order for order in db.orders.values() if order.user_id == current_user.id]
    if status_filter:
        orders = [order for order in orders if order.status == status_filter]
    return orders


@router.get("/{order_id}")
async def get_order(order_id: str, current_user: User = Depends(get_current_user)) -> Order:
    db = get_db()
    order = db.orders.get(order_id)
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/{order_id}")
async def modify_order(
    order_id: str,
    price: float | None = None,
    qty: int | None = None,
    trigger: float | None = None,
    validity: str | None = None,
    current_user: User = Depends(get_current_user),
) -> Order:
    db = get_db()
    order = db.orders.get(order_id)
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if price is not None:
        order.price = price
    if qty is not None:
        order.qty = qty
    if trigger is not None:
        order.trigger = trigger
    if validity is not None:
        order.validity = validity
    order.updated_at = datetime.utcnow()
    return order


@router.post("/{order_id}/cancel")
async def cancel_order(order_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    db = get_db()
    order = db.orders.get(order_id)
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = "CANCELLED"
    order.updated_at = datetime.utcnow()
    return {"detail": "Order cancelled"}


@router.get("/{order_id}/trades")
async def list_trades(order_id: str, current_user: User = Depends(get_current_user)) -> List[Trade]:
    db = get_db()
    order = db.orders.get(order_id)
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    return [trade for trade in db.trades.values() if trade.order_id == order_id]


