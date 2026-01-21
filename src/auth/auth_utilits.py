import jwt
from uuid import uuid4
from hashlib import sha256
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from jwt import ExpiredSignatureError, InvalidTokenError
from src.config import config
import datetime
from fastapi import HTTPException



# --------------------------------------Работа с паролем-----------------------------------------------
ph = PasswordHasher()

# хэширование пароля
async def hash_password(password: str) -> str:
    return ph.hash(password)


# проверка пароля
async def check_password(hashed_password: str, password: str) -> bool:
    try:
        return ph.verify(hashed_password, password)
    except (VerifyMismatchError, InvalidHash):
        return False

# ----------------------------------------Работа с токеном-----------------------------------------
# Хэш токена
def hash_refresh_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()

# Создание рефреш токена
def create_refresh_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "jti": str(uuid4()),
        "type": "refresh",
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=config.auth_data.days)
    }

    token = jwt.encode(
        payload=payload,
        key=config.auth_data.private_key.read_text(),
        algorithm=config.auth_data.algorithm
    )
    return token

# Обновление access token
def decode_refresh_token(token: str) -> dict:
    payload = jwt.decode(
        jwt=token,
        key=config.auth_data.public_key.read_text(),
        algorithms=[config.auth_data.algorithm]
    )

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    return payload

# Создание токена
def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(minutes=config.auth_data.munites)
    }

    return jwt.encode(
        payload=payload,
        key=config.auth_data.private_key.read_text(),
        algorithm=config.auth_data.algorithm
    )


# Декодирование токена
async def decode_access_token(
    token: str,
    algorithm: str = config.auth_data.algorithm,
    public_key: str = config.auth_data.public_key.read_text()
) -> dict:
    """
    Декодирует JWT и возвращает payload.
    Бросает HTTPException при ошибке.
    """
    try:
        payload = jwt.decode(
            jwt=token,
            key=public_key,
            algorithms=[algorithm]
        )
        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    


# Проверка токена
async def verify_access_token(token: str) -> int:
    """
    Проверяет токен, валидирует структуру и возвращает user_id (sub).
    Если токен неверен — вызывает HTTPException.
    """
    payload = await decode_access_token(token)

    # Проверяем стандартное поле sub = user_id
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload: no 'sub'"
        )

    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid user_id format in token"
        )