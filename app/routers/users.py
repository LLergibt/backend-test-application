from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_permission
from app.models.user import User
from app.schemas.auth import MessageOut
from app.schemas.user import UserOut, UserUpdate
from app.services.user_service import (
    get_all_users,
    get_user_by_id,
    soft_delete_user,
    update_user,
    get_user_by_email,
)

router = APIRouter(prefix="/users", tags=["Users"])



@router.get(
    "",
    response_model=list[UserOut],
    dependencies=[Depends(require_permission("users:read_all"))],
)
async def list_users(db: AsyncSession = Depends(get_db)):
    # Требует users:real_all разрешения
    return await get_all_users(db)



@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        _check_permission(current_user, "users:read_all")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user



@router.patch("/{user_id}", response_model=UserOut)
async def patch_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        _check_permission(current_user, "users:update_all")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # prevent email collision
    if data.email and data.email != user.email:
        existing = await get_user_by_email(db, data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )

    return await update_user(db, user, data)



@router.delete("/{user_id}", response_model=MessageOut)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id:
        _check_permission(current_user, "users:delete_all")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await soft_delete_user(db, user)
    return MessageOut(detail="Account deactivated. Please log out.")



def _check_permission(user: User, permission_name: str) -> None:
    user_perms: set[str] = set()
    for role in user.roles:
        for perm in role.permissions:
            user_perms.add(perm.name)
    if permission_name not in user_perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: insufficient permissions",
        )
