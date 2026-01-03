import typing
from binascii import Error
from fastapi import FastAPI
from src.db import engine,Base

from src.models.UserModel import User, PasswordResetToken
from src.models.ChannelModel import Channel, Subscriptions
from src.models.VideoModel import Video, VideoLike
from src.models.CommentModel import Comment

from src.auth.auth_router import app as auth_router
from src.media.media_router import app as media_router
from src.channel.channel_router import app as channel_router



app = FastAPI()

# routers
app.include_router(auth_router)
app.include_router(media_router)
app.include_router(channel_router)


@app.get("/init")
async def create_db():
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.drop_all)
        except Error as e:
            print(e)     
        await  conn.run_sync(Base.metadata.create_all)
    return({"msg":"db creat! =)"})