import typing
import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Text
from src.db import Base

if typing.TYPE_CHECKING:
    from src.models.UserModel import User
    from src.models.VideoModel import Video


class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    # Связи
    # Связь с таблицами User и Video
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    video_id: Mapped[int] = mapped_column(ForeignKey("video.id"))

    user: Mapped["User"] = relationship(back_populates="comments")
    video: Mapped["Video"] = relationship(back_populates="comments")
