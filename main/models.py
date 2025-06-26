from typing import Any, Dict, List

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship

from main.database import Base

# Ассоциативная таблица many-to-many для лайков
like_table = Table(
    "like",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
    Column("tweet_id", Integer, ForeignKey("tweet.id"), primary_key=True),
)

# Ассоциативная таблица для связи many-to-many между пользователями (following/followers)
user_follow_table = Table(
    "user_follow",
    Base.metadata,
    Column(
        "follower_id",
        Integer,
        ForeignKey("user.id"),
        primary_key=True,
    ),
    Column(
        "following_id",
        Integer,
        ForeignKey("user.id"),
        primary_key=True,
    ),
    CheckConstraint("follower_id != following_id", name="check_follower_not_following"),
)


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    api_key = Column(String(20), unique=True, nullable=False)  # noqa: WPS432
    name = Column(String(100), nullable=False)

    liked_tweets: Mapped[List["User"]] = relationship(
        "Tweet", secondary=like_table, back_populates="users_who_liked"
    )

    tweets: Mapped[List["Tweet"]] = relationship(
        "Tweet", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    # Пользователи, на которых подписан текущий пользователь
    following: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_follow_table,
        primaryjoin=id == user_follow_table.c.follower_id,
        secondaryjoin=id == user_follow_table.c.following_id,
        back_populates="followers",
    )

    # Пользователи, которые подписаны на текущего пользователя
    followers: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_follow_table,
        primaryjoin=id == user_follow_table.c.following_id,
        secondaryjoin=id == user_follow_table.c.follower_id,
        back_populates="following",
    )

    def __getitem__(self, point):
        return getattr(self, point)

    def to_json(self) -> Dict[str, Any]:
        result_json = {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
            if column.name != "api_key"
        }
        return result_json


class Tweet(Base):
    __tablename__ = "tweet"

    id = Column(Integer, primary_key=True)
    user_maker_id = Column(
        Integer, ForeignKey("user.id", ondelete="RESTRICT"), nullable=False
    )
    content = Column(Text, nullable=False)
    attachments = Column(JSONB)

    users_who_liked: Mapped[List["User"]] = relationship(
        "User", secondary=like_table, back_populates="liked_tweets"
    )

    user: Mapped["User"] = relationship("User", back_populates="tweets")

    def __getitem__(self, point):
        return getattr(self, point)

    def to_json(self) -> Dict[str, Any]:
        result_json = {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
            if column.name != "user_maker_id"
        }
        return result_json
