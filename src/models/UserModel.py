import typing
import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from src.db import Base

if typing.TYPE_CHECKING:
    from src.models.VideoModel import Video
    from src.models.CommentModel import Comment


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    dob: Mapped[datetime.date] = mapped_column(nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)

    # Связи
    # Связь с таблицей Video
    videos: Mapped[list["Video"]] = relationship(back_populates="author", cascade="all, delete-orphan")
    # Связь с таблицей Comment
    comments: Mapped[list["Comment"]] = relationship(back_populates="user", cascade="all, delete-orphan")