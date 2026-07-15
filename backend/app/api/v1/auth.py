"""Authentication endpoints: register, login, current user, profile update."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.domain.models import User
from app.domain.schemas import (
    AuthTokenOut,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UserOut,
)

router = APIRouter()

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _CREDENTIALS_EXC
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except Exception:  # noqa: BLE001  (any JWT error -> unauthorized)
        raise _CREDENTIALS_EXC
    if not user_id:
        raise _CREDENTIALS_EXC
    user = (
        await session.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise _CREDENTIALS_EXC
    return user


@router.post("/auth/register", response_model=AuthTokenOut, status_code=201)
async def register(
    body: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> AuthTokenOut:
    email = body.email.strip().lower()
    exists = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    session.add(user)
    await session.flush()
    token = create_access_token(user.id)
    return AuthTokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/auth/login", response_model=AuthTokenOut)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> AuthTokenOut:
    email = body.email.strip().lower()
    user = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.id)
    return AuthTokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/auth/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current)


@router.patch("/auth/me", response_model=UserOut)
async def update_me(
    body: UpdateProfileRequest,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    if body.name is not None:
        current.name = body.name.strip()
    if body.avatar_url is not None:
        current.avatar_url = body.avatar_url or None
    session.add(current)
    await session.flush()
    return UserOut.model_validate(current)
