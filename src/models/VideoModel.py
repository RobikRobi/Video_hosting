import typing
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, BigInteger, UniqueConstraint
from src.db import Base

if typing.TYPE_CHECKING:
    from src.models.UserModel import User
    from src.models.CommentModel import Comment


class Video(Base):
    __tablename__="video"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title:Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Связи
    # Связь с таблицей User
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    author: Mapped["User"] = relationship(back_populates="videos")
    # Связь с таблицей Comment
    comments: Mapped[list["Comment"]] = relationship(back_populates="video", cascade="all, delete-orphan")


class VideoLike(Base):
    __tablename__ = "video_like"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("video.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_user_video_like"),
    )