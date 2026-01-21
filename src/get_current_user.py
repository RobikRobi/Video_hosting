from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.db import get_session
from src.models.UserModel import User
from sqlalchemy import select
from src.auth.auth_utilits import verify_access_token




bearer = HTTPBearer(auto_error=True)

async def get_current_id(token: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    return await verify_access_token(token.credentials)

async def get_current_user(
    user_id: int = Depends(get_current_id),
    session: AsyncSession = Depends(get_session)
) -> User:
    user = await session.scalar(
        select(User).where(User.id == user_id)
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )

    return user

