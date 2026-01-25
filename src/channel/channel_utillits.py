from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.db import get_session
from src.models.ChannelModel import Channel
from src.models.UserModel import User
from src.get_current_user import get_current_user




# Функция для проверки наличия Канала в БД
async def get_channel_or_404(
    channel_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Channel:
    stmt = (
        select(Channel)
        .where(Channel.id == channel_id)
        .options(selectinload(Channel.owner))
    )

    channel = await session.scalar(stmt)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )

    return channel

# Функция для проверки владельца канала
async def get_owned_channel(
    channel: Channel = Depends(get_channel_or_404),
    user: User = Depends(get_current_user),
) -> Channel:
    if channel.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this channel",
        )

    return channel