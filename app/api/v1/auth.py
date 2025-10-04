from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserCreate, UserPublic, UserUpdate
from app.services.storage import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic)
async def register(user_in: UserCreate) -> UserPublic:
    db = get_db()
    if any(user.email == user_in.email for user in db.users.values()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(**user_in.dict(exclude={"password"}))
    user.password_hash = get_password_hash(user_in.password)  # type: ignore[attr-defined]
    db.users[user.id] = user
    db.get_or_create_wallet(user.id)
    return UserPublic.from_orm(user)


@router.post("/login")
async def login(email: str, password: str) -> Dict[str, Any]:
    db = get_db()
    for user in db.users.values():
        password_hash: Optional[str] = getattr(user, "password_hash", None)
        if user.email == email and password_hash and verify_password(password, password_hash):
            token = create_access_token(subject=user.id, roles=user.roles)
            return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/logout")
async def logout() -> Dict[str, str]:
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserPublic)
async def read_me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.from_orm(current_user)


@router.put("/me", response_model=UserPublic)
async def update_me(
    update: UserUpdate,
    current_user: User = Depends(get_current_user),
) -> UserPublic:
    for field, value in update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    return UserPublic.from_orm(current_user)


@router.post("/password/change")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    password_hash: Optional[str] = getattr(current_user, "password_hash", None)
    if not password_hash or not verify_password(old_password, password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid password")
    current_user.password_hash = get_password_hash(new_password)  # type: ignore[attr-defined]
    current_user.updated_at = datetime.utcnow()  # type: ignore[attr-defined]
    return {"detail": "Password changed"}


@router.post("/password/reset")
async def reset_password(email: str) -> Dict[str, str]:
    db = get_db()
    if not any(user.email == email for user in db.users.values()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"detail": "Password reset instructions sent"}


@router.get("/roles")
async def get_roles(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    return {"roles": current_user.roles}
