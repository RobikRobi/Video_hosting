import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.UserModel import User
from src.auth.auth_shema import RegisterUser, ShowUser, LoginUser
from fastapi import HTTPException
from src.db import get_session
from src.auth.auth_utilits import create_access_token, hash_password, check_password
from src.get_current_user import get_current_user
from src.celery_app import send_email
from src.auth.auth_shema import PasswordResetRequest, PasswordResetConfirm
from src.models.UserModel import PasswordResetToken

app = APIRouter(prefix="/users", tags=["Users"])

# Получение пользователя
@app.get("/me", response_model=ShowUser)
async def me(me = Depends(get_current_user)):
     return me

# Авторизация пользователя
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


subject = "Регистрация на сайте VideoHosting"
text = """
Здравствуйте!

Спасибо, что зарегистрировались на нашем сайте.

Теперь Вы можете не только смотреть чужие видео, но и создавать свои видео. 

А также делится своим контентом на собственном канале.

Надеемся на долгое и плодотворное сотрудничество с Вами.

С уважением, администрация хостинга
"""
# Регистрация пользователя с отправкой сообщения на email
@app.post("/register")
async def register_user(data:RegisterUser, session:AsyncSession = Depends(get_session)):
    
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
    await session.flush([user])

    user_id = user.id
        
    await session.commit()
    send_email.delay(user.email, subject, text)
        
    user_token = await create_access_token(user_id=user_id)
    data_dict["token"] = user_token  
        
    return data_dict

# Запрос на восстановление пароля
@app.post("/password-reset")
async def password_reset_request(
    data: PasswordResetRequest,
    session: AsyncSession = Depends(get_session)
):
    user = await session.scalar(
        select(User).where(User.email == data.email)
    )

    #не раскрываем, существует ли пользователь
    if not user:
        return {"status": "ok"}

    token = str(uuid.uuid4())

    reset_token = PasswordResetToken(
        token=token,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(minutes=30)
    )

    session.add(reset_token)
    await session.commit()

    reset_link = f"https://your-frontend/reset-password?token={token}"

    send_email.delay(
        user.email,
        "Восстановление пароля",
        f"Перейдите по ссылке для восстановления пароля:\n{reset_link}"
    )

    return {"status": "ok"}

# Подтверждение и смена пароля
@app.post("/password-reset/confirm")
async def password_reset_confirm(
    data: PasswordResetConfirm,
    session: AsyncSession = Depends(get_session)
):
    token_obj = await session.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token == data.token)
    )

    if not token_obj or token_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await session.get(User, token_obj.user_id)

    user.password = await hash_password(data.new_password)

    await session.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id
        )
    )

    await session.commit()

    return {"status": "password updated"}