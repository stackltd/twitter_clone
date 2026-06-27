import sys
import time
from contextlib import asynccontextmanager

import uvicorn
from asyncpg.exceptions import CannotConnectNowError
from fastapi import FastAPI
from loguru import logger
from sqlalchemy import (
    select,
)

from main.database import AsyncSessionLocal, engine, Base, session
from main.models import User
from main.routes import router
from main.dao import DAO


logger.remove()
format_out = "{module} <green>{time:DD-MM-YYYY HH:mm:ss}</green> {level} <level>{message}</level>"
logger.add(sys.stdout, format=format_out, level="INFO", colorize=True)
logger.level("WARNING", color="<fg 10,190,200>")


status_code_error = 400


async def init_models():
    """
    Функция создания таблиц
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_data():
    """
    Функция создания начальных данных для вновь созданной таблицы
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).limit(1))
            user_exists = result.scalars().first()
            if not user_exists:
                await DAO.seed_data_statement(session)
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    lifespan
    """
    try:
        logger.info("startup")
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            await init_models()
            await seed_data()
        yield
    except (ConnectionRefusedError, ConnectionError, CannotConnectNowError) as ex:
        logger.error(ex)
        logger.info("Ждем окончания инициализации базы данных")
        time.sleep(10)
        async with engine.begin() as conn:
            await init_models()
            await seed_data()
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        yield
    logger.info("Shutdown")
    await session.close()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


app.include_router(router)

if __name__ == "__main__":
    port = 8000
    uvicorn.run("app:app", port=port)
