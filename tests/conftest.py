import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main.app import app, logger
from main.database import Base, session
from main.utils import seed_data_statement

TEST_DATABASE_URL = "postgresql+asyncpg://admin:admin@localhost:5433/twitter"


# Создаем движок и сессию для тестов
engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncSessionTest = async_sessionmaker(
    engine_test, expire_on_commit=False, class_=AsyncSession
)


# Переопределяем зависимость get_session в FastAPI
async def override_get_session() -> AsyncSession:
    async with AsyncSessionTest() as session:
        yield session


app.dependency_overrides[session] = override_get_session


@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Заполнение тестовыми данными
    async with AsyncSessionTest() as session:
        try:
            logger.info("Создание данных")
            await seed_data_statement(session=session)
            await session.commit()
        except IntegrityError as ex:
            logger.error(ex)

    yield

    async with engine_test.begin() as conn:
        logger.info("Удаление данных")
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://") as client:
        yield client


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
