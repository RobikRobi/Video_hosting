import datetime
import typing
from sqlalchemy import ForeignKey
from src.db import Base
from sqlalchemy.orm import Mapped, mapped_column



class User(Base):
    __tablename__ = "user_table"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    dob: Mapped[datetime.date]
    password: Mapped[bytes]
    