import typing
import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from src.db import Base

if typing.TYPE_CHECKING:
    from src.models.VideoModel import Video
    from src.models.CommentModel import Comment
    from src.models.ChannelModel import Channel
    from src.models.ChannelModel import Subscriptions


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    dob: Mapped[datetime.date] = mapped_column(nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)

    # Связи
    # Видео пользователя
    videos: Mapped[list["Video"]] = relationship(back_populates="author", 
                                                 cascade="all, delete-orphan")
    # Комментарии пользователя
    comments: Mapped[list["Comment"]] = relationship(back_populates="user", 
                                                     cascade="all, delete-orphan")
    # Канал пользователя
    channel: Mapped["Channel"] = relationship(back_populates="owner", 
                                              uselist=False,
                                              cascade="all, delete-orphan")

    # Подписки пользователя
    subscriptions: Mapped[list["Subscriptions"]] = relationship(back_populates="user", 
                                                          cascade="all, delete-orphan")



# Модель токена восстановления
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime.datetime]