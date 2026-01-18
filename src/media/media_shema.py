import datetime
from pydantic import BaseModel
from src.models.UserModel import User

class UserShow(BaseModel):
    id: int
    login: str

    class Config:
        from_attributes = True


class ChannelShow(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class VideoShow(BaseModel):
    title: str
    description: str
    views: int
    likes: int
    author: UserShow
    channel: ChannelShow

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    text: str

class CommentUpdate(BaseModel):
    text: str

class CommentOut(BaseModel):
    id: int
    text: str
    created_at: datetime.datetime
    user_id: int
    video_id: int

    class Config:
        from_attributes = True