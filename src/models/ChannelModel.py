import typing
import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from sqlalchemy import func
from src.db import Base

if typing.TYPE_CHECKING:
    from src.models.UserModel import User
    from src.models.VideoModel import Video
    



class Channel(Base):
    __tablename__ = "channel"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                  ForeignKey("channel.id", ondelete="CASCADE"),
                                                  primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    channel: Mapped["Channel"] = relationship(back_populates="subscribers")