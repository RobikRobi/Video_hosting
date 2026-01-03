from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db import get_session
from src.get_current_user import get_current_user
from src.channel.channel_shema import CreateChannel
from src.models.UserModel import User
from src.models.ChannelModel import Channel



app = APIRouter(prefix="/channel", tags=["Channel"])

# Создание канала
@app.post("/", status_code=status.HTTP_201_CREATED)
async def create_channel(
    data: CreateChannel,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Проверяем, есть ли уже канал
    result = await session.execute(
        select(Channel).where(Channel.owner_id == user.id)
    )
    existing_channel = result.scalar_one_or_none()

    if existing_channel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a channel",
        )

    new_channel = Channel(
        title=data.title.strip(),
        description=data.description.strip(),
        img=data.img,
        owner_id=user.id,
    )

    session.add(new_channel)
    await session.commit()
    await session.refresh(new_channel)

    return new_channel