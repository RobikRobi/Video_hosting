from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.db import get_session
from src.models.UserModel import User
from sqlalchemy import select
from src.auth.auth_utilits import valid_access_token

bearer = HTTPBearer()
  

async def get_current_id(token:HTTPAuthorizationCredentials = Depends(bearer)):
    user_id = await valid_access_token(token=token.credentials)
    if not user_id:
        raise HTTPException(status_code=426, detail={
            "token":"Your token is not valid",
            "status":426
         })
    return user_id

async def get_current_user(user_id = Depends(get_current_id), session:AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).options(selectinload(User.profile), selectinload(User.backet)).where(User.id == user_id))

    if not user:
        raise HTTPException(status_code=426,detail={
            "token":"Your token is not valid", 
            "status":426
        })
    
    return user

