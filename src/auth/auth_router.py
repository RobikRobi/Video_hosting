from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.UserModel import User
from src.auth.auth_shema import RegisterUser, ShowUser, LoginUser
from fastapi import HTTPException
from src.db import get_session
from src.auth.auth_utilits import create_access_token, hash_password, check_password
from src.get_current_user import get_current_user

app = APIRouter(prefix="/users", tags=["Users"])

@app.get("/me", response_model=ShowUser)
async def me(me = Depends(get_current_user)):
     return me


@app.post("/login")
async def login_user(data:LoginUser,session:AsyncSession = Depends(get_session)):

    user = await session.scalar(select(User).where(User.email == data.email))

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not await check_password(user.password, data.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = await create_access_token(user_id=user.id)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@app.post("/register")
async def register_user(data:RegisterUser ,session:AsyncSession = Depends(get_session)):
    
    isUserEx = await session.scalar(select(User).where(User.email == data.email))
    
    if isUserEx:
        raise HTTPException(status_code=411, detail={
        "status":411,
        "data":"user is exists"
        })
        
    data_dict = data.model_dump()
        
    data_dict["password"] = await hash_password(password=data.password)
    
    user = User(**data_dict)
    session.add(user) 
    await session.flush()

    user_id = user.id
        
    await session.commit()
        
    user_token = await create_access_token(user_id=user_id)
    data_dict["token"] = user_token  
        
    return data_dict