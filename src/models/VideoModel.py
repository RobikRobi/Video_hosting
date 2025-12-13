import typing
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from db import Base

if typing.TYPE_CHECKING:
    from src.models.UserModel import User
    from src.models.CommentModel import Comment


class Video(Base):
    __tablename__="video"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title:Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)

    # Связи
    # Связь с таблицей User
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    author: Mapped["User"] = relationship(back_populates="videos")
    # Связь с таблицей Comment
    comments: Mapped[list["Comment"]] = relationship(back_populates="video", cascade="all, delete-orphan")
