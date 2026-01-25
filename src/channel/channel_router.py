from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.db import get_session
from src.get_current_user import get_current_user
from src.channel.channel_shema import CreateChannel, ShowChannel, SubscriptionChannelOut, ChannelUpdate
from src.models.UserModel import User
from src.models.ChannelModel import Channel, Subscriptions



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
    channel_id: UUID, 
    session: AsyncSession = Depends(get_session)):
    stmt = select(Channel).where(Channel.id == channel_id).options(selectinload(Channel.owner))
    channel = await session.scalar(stmt)

    if not channel:
        raise HTTPException(status_code=400, detail="Channel not found")
    return channel

# Редактирование канала
@app.put("/{channel_id}", response_model=ShowChannel)
async def update_channel(
    data: ChannelUpdate,
    channel_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Channel)
        .where(Channel.id == channel_id)
        .options(selectinload(Channel.owner))
    )

    channel = await session.scalar(stmt)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.owner_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to edit this channel"
        )

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field, value in update_data.items():
        setattr(channel, field, value)

    try:
        await session.commit()
        await session.refresh(channel)
        return channel

    except Exception:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to update channel")




# Удаление канала по id
@app.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: UUID,
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


# Подписка на канал
@app.post("/{channel_id}/subscribe")
async def subscribe_to_channel(channel_id: UUID,
                  user: User = Depends(get_current_user),
                  session: AsyncSession = Depends(get_session)):
    # Проверяем, существует ли канал
    channel = await session.get(Channel, channel_id)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )
    # Запрещаем подписку на свой канал
    if channel.owner_id == user.id:
        raise HTTPException(
            tatus_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot subscribe to your own channel",
        )
    # Проверяем, есть ли уже подписка
    result = await session.execute(
        select(Subscriptions).where(
            Subscriptions.user_id == user.id,
            Subscriptions.channel_id == channel_id
        )
    )
    existing_subscription = result.scalar_one_or_none()
    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already subscribed to this channel",
        )
    # Делаем подписку на канал
    subscription = Subscriptions(user_id = user.id, channel_id = channel_id)
    session.add(subscription)
    await session.commit()

    return {"message": "Successfully subscribed"}


# Отписка от канала
@app.delete("/{channel_id}/subscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_from_channel(channel_id: UUID, 
                                   user: User = Depends(get_current_user),
                                   session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Subscriptions).where(
            Subscriptions.user_id == user.id,
            Subscriptions.channel_id == channel_id
        )
    )
    # Проверяем, есть ли подписка на канал
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    await session.delete(subscription)
    await session.commit()

    return {"message": "Successfully unsubscribed"}

# Получение всех подписок пользователя
@app.get("/subscriptions/me", response_model=list[SubscriptionChannelOut])
async def get_my_subscriptions(user: User = Depends(get_current_user), 
                               session: AsyncSession = Depends(get_session)):
    stmt = (select(Channel.id.label("channel_id"),
                  Channel.title,
                  Channel.description,
                  Channel.img,
                  Subscriptions.created_at.label("subscribed_at"))
                  .join(Subscriptions, Subscriptions.channel_id == Channel.id)
                  .where(Subscriptions.user_id == user.id)
                  .order_by(Subscriptions.created_at.desc())
                  )
    result = await session.execute(stmt)
    rows = result.all()

    return rows