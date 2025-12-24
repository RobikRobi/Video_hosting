from pydantic import BaseModel
from src.models.UserModel import User

class UserShow(BaseModel):
    id: int
    login: str

    class Config:
        from_attributes = True

class VideoShow(BaseModel):
    title: str
    description: str
    views: int
    author: UserShow

    class Config:
        from_attributes = True