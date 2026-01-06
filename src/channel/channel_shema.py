from pydantic import BaseModel, Field
from src.media.media_shema import UserShow


# Схема для созадния канала
class CreateChannel(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10)
    img: str | None = None


class ShowChannel(BaseModel):
    title: str
    description: str
    img: str | None = None
    owner: UserShow

    class Config:
        from_attributes = True