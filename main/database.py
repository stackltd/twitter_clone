import os
from typing import AsyncGenerator

from dotenv import find_dotenv, load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


load_dotenv(find_dotenv())


login = os.getenv("db_login")
password = os.getenv("db_password")
name = os.getenv("db_name")
db_host = os.getenv("db_host")


port = int(os.getenv("db_port"))

DATABASE_URL = f"postgresql+asyncpg://{login}:{password}@{db_host}:{port}/{name}"


engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)
session = AsyncSessionLocal()


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
