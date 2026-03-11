import uuid
import dropbox
from fastapi import APIRouter, Depends, HTTPException,  UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db import get_session
from src.config import config
from src.get_current_user import get_current_user
from src.channel.channel_shema import CreateChannel, ShowChannel, SubscriptionChannelOut, ChannelUpdate
from src.models.UserModel import User
from src.models.ChannelModel import Channel, Subscriptions
from src.channel.channel_utillits import get_channel_or_404, get_owned_channel


app = APIRouter(prefix="/channel", tags=["Channel"])


dbx = dropbox.Dropbox(
    oauth2_refresh_token=config.env_data.DROPBOX_REFRESH_TOKEN,
    app_key=config.env_data.DROPBOX_APP_KEY,
    app_secret=config.env_data.DROPBOX_APP_SECRET,
)

# Создание канала
@app.post("/", status_code=status.HTTP_201_CREATED)
async def create_channel(
    title: str = Form(...),
    description: str = Form(...),
    avatar: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):

    result = await session.execute(
        select(Channel).where(Channel.owner_id == user.id)
    )
    existing_channel = result.scalar_one_or_none()

    if existing_channel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a channel",
        )

    img_path = None

    if avatar:
        ext = avatar.filename.split(".")[-1]
        img_id = uuid.uuid4()

        dropbox_path = f"/images/{img_id}.{ext}"

        file_bytes = await avatar.read()

        dbx.files_upload(
            file_bytes,
            dropbox_path,
            mode=dropbox.files.WriteMode.overwrite
        )

        img_path = dropbox_path

    new_channel = Channel(
        title=title.strip(),
        description=description.strip(),
        img=img_path,
        owner_id=user.id,
    )

    session.add(new_channel)
    await session.commit()
    await session.refresh(new_channel)

    return new_channel

# получение канала по id
@app.get("/{channel_id}", response_model=ShowChannel)
async def get_channel(channel: Channel = Depends(get_channel_or_404)):
    return channel

# Редактирование канала
@app.put("/{channel_id}", response_model=ShowChannel)
async def update_channel(
    data: ChannelUpdate,
    channel: Channel = Depends(get_owned_channel),
    session: AsyncSession = Depends(get_session),
):
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field, value in update_data.items():
        setattr(channel, field, value)

    await session.commit()
    await session.refresh(channel)
    return channel


# Удаление канала по id
@app.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel: Channel = Depends(get_owned_channel),
    session: AsyncSession = Depends(get_session),
):
    await session.delete(channel)
    await session.commit()


# Подписка на канал
@app.post("/{channel_id}/subscribe")
async def subscribe_to_channel(
    channel: Channel = Depends(get_channel_or_404),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if channel.owner_id == user.id:
        raise HTTPException(400, "You cannot subscribe to your own channel")

    result = await session.execute(
        select(Subscriptions).where(
            Subscriptions.user_id == user.id,
            Subscriptions.channel_id == channel.id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(400, "Already subscribed")

    session.add(Subscriptions(user_id=user.id, channel_id=channel.id))
    await session.commit()

    return {"message": "Subscribed"}


# Отписка от канала
@app.delete("/{channel_id}/subscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_from_channel(channel_id: uuid.UUID, 
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