from typing import Dict, List, Optional

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_admin
from app.models.common import Notification
from app.models.user import User
from app.services.storage import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(current_user: User = Depends(get_current_user)) -> List[Notification]:
    db = get_db()
    return [notification for notification in db.notifications.values() if notification.user_id in {None, current_user.id}]


@router.post("")
async def create_notification(
    title: str,
    body: str,
    user_id: Optional[str] = None,
    _: User = Depends(require_admin),
) -> Notification:
    db = get_db()
    notification = Notification(user_id=user_id, title=title, body=body)
    db.notifications[notification.id] = notification
    return notification
