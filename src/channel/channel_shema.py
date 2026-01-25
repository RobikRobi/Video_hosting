import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from src.media.media_shema import UserShow


# Схема для созадния канала
class CreateChannel(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10)
    img: str | None = None

# Схема для получения канала
class ShowChannel(BaseModel):
    title: str
    description: str
    img: str | None = None
    owner: UserShow

    class Config:
        from_attributes = True

# Схема для получения списка подписок пользователя
class SubscriptionChannelOut(BaseModel):
    channel_id: UUID
    title: str
    description: str
    img: str | None
    subscribed_at: datetime.datetime

    class Config:
        from_attributes = True

class ChannelUpdate(BaseModel):
    title: str | None 
    description: str | None
    img: str | None = None