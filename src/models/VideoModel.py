import typing
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, BigInteger, UniqueConstraint
from src.db import Base

if typing.TYPE_CHECKING:
    from src.models.UserModel import User
    from src.models.ChannelModel import Channel
    from src.models.CommentModel import Comment
    


class Video(Base):
    __tablename__="video"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title:Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
<<<<<<< HEAD
    storage_path: Mapped[str] = mapped_column(nullable=False) #DropBox path
=======
    storage_path: Mapped[str] = mapped_column(nullable=False)
>>>>>>> fix-video-stream
    views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Связи
    # Автор видео
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"),
                                                      nullable=True)
     # SET NULL, если пользователь будет удалён — поле author_id у видео станет NULL, 
     # а само видео останется.
    author: Mapped["User"] = relationship()
    # Комментарии
    comments: Mapped[list["Comment"]] = relationship(back_populates="video", 
                                                     cascade="all, delete-orphan")
    # Канал, где размещено видео
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), 
                                                  ForeignKey("channel.id", ondelete="CASCADE"),
                                                  nullable=False,
                                                  index=True)
    
    channel: Mapped["Channel"] = relationship(back_populates="videos")

# таблица-модель (join entity)
class VideoLike(Base):
    __tablename__ = "video_like"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
        ForeignKey("video.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_user_video_like"),
    )