import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from src.db import Base


class User(Base):
    __tablename__ = "user_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    dob: Mapped[datetime.date] = mapped_column(nullable=False)

    password: Mapped[str] = mapped_column(String, nullable=False)
