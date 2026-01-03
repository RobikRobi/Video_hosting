import typing
import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, BigInteger, UniqueConstraint
from src.db import Base

if typing.TYPE_CHECKING:
    from src.models.UserModel import User
    from src.models.VideoModel import Video
    



class Channel(Base):
    __tablename__ = "channel"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False)
    description:Mapped[str] = mapped_column(nullable=False)
    img: Mapped[str]  = mapped_column(nullable=True)

    # Связи
    # Владелец канала
    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"),
                                          unique=True,
                                          nullable=False)
    owner: Mapped["User"] = relationship(back_populates="channel", uselist=False)

    # Видео на канале
    videos: Mapped[list["Video"]] = relationship(back_populates="channel",
                                                 cascade="all, delete-orphan")

    # Подписчики канала
    subscribers: Mapped[list["Subscriptions"]] = relationship(back_populates="channel", 
                                                              cascade="all, delete-orphan")
    

class Subscriptions(Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), 
                                         primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channel.id", ondelete="CASCADE"),
                                            primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.timezone.utc)

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    channel: Mapped["Channel"] = relationship(back_populates="subscribers")