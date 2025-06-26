import os
import shutil
import sys
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from asyncpg.exceptions import CannotConnectNowError
from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, FastAPI, File, Header, Path, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import (
    and_,
    select,
)
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

load_dotenv(find_dotenv())


from main.database import AsyncSessionLocal, Base, engine, session
from main.models import Tweet, User
from main.schemas import (
    ErrorResponse,
    FileSendOut,
    GetTweets,
    GetUserProfile,
    Result,
    SendTweet,
    SendTweetOut,
    UserInPost,
)
from main.utils import (
    errors,
    follow_control,
    get_followed_ids,
    get_last_tweet_id,
    get_profile,
    get_tweets_ordered_from_like,
    like_control,
    seed_data_statement,
    tweet_data,
)

logger.remove()
format_out = "{module} <green>{time:DD-MM-YYYY HH:mm:ss}</green> {level} <level>{message}</level>"
logger.add(sys.stdout, format=format_out, level="INFO", colorize=True)
logger.level("WARNING", color="<fg 10,190,200>")


status_code_error = 400
description_id_user = "id пользователя"
token = os.getenv("token")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


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
                await seed_data_statement(session)
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
            # await conn.run_sync(Base.metadata.create_all)
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
            # await conn.run_sync(Base.metadata.create_all)
        yield
    logger.info("Shutdown")
    await session.close()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


class AuthorizationError(Exception):
    def __init__(self, error_message: str):
        self.args = (error_message,)


@app.exception_handler(AuthorizationError)
async def custom_api_exception_handler(request: Request, exc: AuthorizationError):
    """
    Функция перехвата ошибок авторизации AuthorizationError
    """
    return JSONResponse(
        status_code=status_code_error,
        content={"result": False},  # noqa: WPS226
    )


@app.exception_handler(ResponseValidationError)
async def validation_response_exception_handler(
    request: Request, exc: ResponseValidationError
):
    """
    Функция перехвата ошибок валидации в Response
    """
    error_body = exc.body
    error = {
        "result": False,
        "error_type": error_body["error_type"],
        "error_message": error_body["error_message"],
    }
    return JSONResponse(error, status_code=status_code_error)


@app.exception_handler(RequestValidationError)
async def validation_request_exception_handler(
    request: Request, exc: RequestValidationError
):
    """
    Функция перехвата ошибок валидации в Request
    """
    error_body = exc.errors()[0]
    error = {
        "result": False,
        "error_type": error_body["type"],
        "error_message": error_body["msg"],
    }
    return JSONResponse(error, status_code=status_code_error)


@app.get("/api/tweets", description="Лента пользователя", response_model=GetTweets)
async def tweets(
    api_key: str = Header(...), session=Depends(get_session)
):  # noqa: WPS204,WPS231
    try:
        followed_ids = await get_followed_ids(api_key, session)
        tweet_id_last = await get_last_tweet_id(
            user_id=followed_ids["user_id"], session=session
        )
        result_all = await get_tweets_ordered_from_like(
            following_ids=followed_ids["following_ids"], session=session
        )
        # ставим на первое место последний твит пользователя
        if tweet_id_last:
            for index, tweet in enumerate(result_all):
                if tweet["id"] == tweet_id_last and isinstance(result_all, list):
                    result_all.insert(0, result_all.pop(index))
                    break

        return {"result": True} | {"tweets": result_all}
    except AttributeError as ex:
        return errors(ex)


@app.get(
    "/api/users/me",
    description="Получить данные своего профиля",
    response_model=GetUserProfile,
)
async def get_my_profile(
    response: Response,
    api_key: str = Header(...),
    session=Depends(get_session),
):
    profile = await get_profile(
        field="api_key", field_value=api_key, response=response, session=session
    )
    return profile


@app.get(
    "/api/users/{id}",
    description="Получить данные о произвольном профиле",
    response_model=GetUserProfile,
)
async def get_some_profile(
    response: Response,
    id: int = Path(..., gt=0, description=description_id_user),
    session=Depends(get_session),
):
    profile = await get_profile(
        field="id", field_value=id, response=response, session=session
    )
    return profile


@app.post(
    "/api/users/{id}/follow",
    description="Подписка на пользователя",
    response_model=Result | ErrorResponse,
)
async def follow(
    api_key: str = Header(...),
    id: int = Path(..., gt=0, description=description_id_user),
    session=Depends(get_session),
):
    follow_result = await follow_control(
        id=id, api_key=api_key, method_name="append", session=session
    )
    return follow_result


@app.delete(
    "/api/users/{id}/follow",
    description="Отписка от пользователя",
    response_model=Result | ErrorResponse,
)
async def unfollow(
    api_key: str = Header(...),
    id: int = Path(..., gt=0, description=description_id_user),
    session=Depends(get_session),
):
    unfollow_result = await follow_control(
        id=id, api_key=api_key, method_name="remove", session=session
    )
    return unfollow_result


@app.post(
    "/api/tweets/{id}/likes",
    description="Установка лайка",
    response_model=Result | ErrorResponse,
)
async def set_like(
    api_key: str = Header(...),
    id: int = Path(..., gt=0, description="id твита"),
    session=Depends(get_session),
):
    set_like_result = await like_control(
        like_id=id, api_key=api_key, method_name="append", session=session
    )
    return set_like_result


@app.delete(
    "/api/tweets/{id}/likes",
    description="Снятие лайка",
    response_model=Result | ErrorResponse,
)
async def delete_like(
    api_key: str = Header(...),
    id: int = Path(..., gt=0, description="id твита"),
    session=Depends(get_session),
):
    delete_like_result = await like_control(
        like_id=id, api_key=api_key, method_name="remove", session=session
    )
    return delete_like_result


@app.post(
    "/api/make_user", description="Создание пользователя", response_model=UserInPost
)
async def make_user(user: UserInPost, authorization_token: str = Header(...)):
    try:
        if authorization_token != token:
            raise AuthorizationError(error_message="Ошибка авторизации")
        async with session.begin():
            new_user = User(**user.dict())
            session.add(new_user)
            # await session.commit()
        return new_user
    except (AuthorizationError, IntegrityError) as ex:
        return errors(ex)


@app.delete(
    "/api/delete_user/{id}",
    description="Удаление пользователя",
    response_model=Result | ErrorResponse,
)
async def delete_user(
    authorization_token: str = Header(...),
    id: int = Path(..., gt=0, description=description_id_user),
):
    try:
        if authorization_token != token:
            raise AuthorizationError(error_message="Ошибка авторизации")
        async with session.begin():
            user_object = await session.execute(select(User).filter_by(id=id))
            user = user_object.scalar_one()
            await session.delete(user)
            await session.commit()
        return {"result": True}
    except (NoResultFound, AuthorizationError) as ex:
        return errors(ex)


@app.post("/api/medias", description="Отправка файла", response_model=FileSendOut)
async def send_file(file: UploadFile = File(...)):
    UPLOAD_DIR = "images/"
    root_dir = os.path.dirname(os.path.abspath(__file__))
    name = file.filename
    file_in_container = os.path.join(root_dir, UPLOAD_DIR, name)
    file_in_server = os.path.join(UPLOAD_DIR, name)
    with open(file_in_container, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"result": True} | {"media_id": file_in_server}


@app.post("/api/tweets", response_model=SendTweetOut, description="Отправка твита")
async def send_tweet(
    tweets: SendTweet,
    api_key: str = Header(...),
    session=Depends(get_session),
):
    try:
        async with session.begin():
            user = await session.execute(select(User.id).filter_by(api_key=api_key))
            user_id = user.scalar_one()
            data_in = tweet_data(tweets)
            data_in.update({"user_maker_id": user_id})
            new_tweet = Tweet(**data_in)
            session.add(new_tweet)
        return {"result": True} | {"tweet_id": new_tweet.id}
    except NoResultFound as ex:
        return errors(ex)


@app.delete(
    "/api/tweets/{id}",
    description="Удаление твита",
    response_model=Result | ErrorResponse,
)
async def delete_tweet(
    response: Response,
    api_key: str = Header(...),
    session=Depends(get_session),
    id: int = Path(..., gt=0, description="id твита"),
):
    try:
        async with session.begin():
            tweet_object = await session.execute(
                select(Tweet)
                .join(User)
                .filter(and_(Tweet.id == id, User.api_key == api_key))
            )
            tweet = tweet_object.scalar_one()
            await session.delete(tweet)
            await session.commit()
        return {"result": True}
    except NoResultFound as ex:
        response.status_code = 401
        return errors(ex)


if __name__ == "__main__":
    port = 8000
    uvicorn.run("app:app", port=port)
