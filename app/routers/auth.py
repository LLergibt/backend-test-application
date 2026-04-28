from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, decode_token, verify_password
from app.dependencies.auth import get_current_user
from app.models.rbac import Role, UserRole
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User
from app.schemas.auth import LoginRequest, MessageOut, TokenOut
from app.schemas.user import UserOut, UserRegister
from app.services.user_service import create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer()



async def _assign_default_role(db: AsyncSession, user: User) -> None:
    from sqlalchemy import select

    result = await db.execute(select(Role).where(Role.name == "user"))
    role = result.scalar_one_or_none()
    if role:
        db.add(UserRole(user_id=user.id, role_id=role.id))
        await db.commit()
        await db.refresh(user)



@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = await create_user(db, data)
    await _assign_default_role(db, user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, data.email)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deactivated",
        )
    token = create_access_token(subject=user.id)
    return TokenOut(access_token=token)


@router.post("/logout", response_model=MessageOut)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Поместить токен в блэклист
    token = credentials.credentials
    try:
        payload = decode_token(token)
        exp_ts = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    except JWTError:
        expires_at = datetime.now(timezone.utc)

    db.add(TokenBlacklist(token=token, expires_at=expires_at))
    await db.commit()
    return MessageOut(detail="Successfully logged out")


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
