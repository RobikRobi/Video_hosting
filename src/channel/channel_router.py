from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.db import get_session
from src.get_current_user import get_current_user
from src.channel.channel_shema import CreateChannel, ShowChannel
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

# получение канала по id
@app.get("/{channel_id}", response_model=ShowChannel)
async def get_channel(
    channel_id: int, 
    session: AsyncSession = Depends(get_session)):
    stmt = select(Channel).where(Channel.id == channel_id).options(selectinload(Channel.owner))
    channel = await session.scalar(stmt)

    if not channel:
        raise HTTPException(status_code=400, detail="Channel not found")
    return channel

# Удаление канала по id
@app.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Channel).where(Channel.id == channel_id)
    )
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(status_code=404, detail="Video not found")

    # Проверка владельца
    if channel.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You are not allowed to delete this channel")

    try:
        # Удаляем запись из БД
        await session.delete(channel)
        await session.commit()

    except Exception:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete channel")

    return None