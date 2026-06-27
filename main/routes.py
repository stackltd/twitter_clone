import os
from dotenv import find_dotenv, load_dotenv
from fastapi import Depends, File, Header, Path, Response, UploadFile, APIRouter

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm.exc import UnmappedInstanceError
from main.exceptions import AuthorizationError
from main.services import APIServices

load_dotenv(find_dotenv())

from main.database import get_session
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
from main.dao import errors, DAO

router = APIRouter(prefix="/api", tags=["TwiClone"])

token = os.getenv("token")
description_id_user = "id пользователя"


@router.get(
    "/tweets",
    description="Лента пользователя",
    response_model=GetTweets | ErrorResponse,
)
async def tweets(
    api_key: str = Header(...), session=Depends(get_session)
):  # noqa: WPS204,WPS231
    try:
        result = await APIServices.get_tweets(api_key, session)
        return {"result": True} | {"tweets": result}
    except AttributeError as ex:
        return errors(ex, message=f"Пользователь '{api_key}' не найден")


@router.get(
    "/users/me",
    description="Получить данные своего профиля",
    response_model=GetUserProfile | ErrorResponse,
)
async def get_my_profile(
    response: Response,
    api_key: str = Header(...),
    session=Depends(get_session),
):
    try:
        profile = await DAO.get_profile(
            field="api_key", field_value=api_key, response=response, session=session
        )
        return profile
    except (AttributeError, NoResultFound) as ex:
        response.status_code = 401
        return errors(ex, message=f"Пользователь '{api_key}' не найден")


@router.get(
    "/users/{id}",
    description="Получить данные о произвольном профиле",
    response_model=GetUserProfile | ErrorResponse,
)
async def get_some_profile(
    response: Response,
    id: int = Path(..., gt=0, description=description_id_user),
    session=Depends(get_session),
):
    try:
        profile = await DAO.get_profile(
            field="id", field_value=id, response=response, session=session
        )
        return profile
    except (AttributeError, NoResultFound) as ex:
        response.status_code = 401
        return errors(ex, message=f"Пользователь '{id}' не найден")


@router.post(
    "/users/{id}/follow",
    description="Подписка на пользователя",
    response_model=Result | ErrorResponse,
)
async def follow(
    api_key: str = Header(...),
    id: int = Path(..., gt=0, description=description_id_user),
    session=Depends(get_session),
):
    try:
        follow_result = await DAO.follow_control(
            id=id, api_key=api_key, method_name="append", session=session
        )
        return follow_result
    except (
        ValueError,
        IntegrityError,
        NoResultFound,
    ) as ex:
        return errors(ex)


@router.delete(
    "/users/{id}/follow",
    description="Отписка от пользователя",
    response_model=Result | ErrorResponse,
)
async def unfollow(
    api_key: str = Header(...),
    id: int = Path(..., gt=0, description=description_id_user),
    session=Depends(get_session),
):
    try:
        unfollow_result = await DAO.follow_control(
            id=id, api_key=api_key, method_name="remove", session=session
        )
        return unfollow_result
    except (
        ValueError,
        IntegrityError,
        NoResultFound,
    ) as ex:
        return errors(ex)


@router.post(
    "/tweets/{id}/likes",
    description="Установка лайка",
    response_model=Result | ErrorResponse,
)
async def set_like(
    api_key: str = Header(...),
    id: int = Path(..., gt=0, description="id твита"),
    session=Depends(get_session),
):
    try:
        set_like_result = await DAO.like_control(
            like_id=id, api_key=api_key, method_name="append", session=session
        )
        return set_like_result
    except (
        ValueError,
        IntegrityError,
        NoResultFound,
    ) as ex:
        return errors(ex)


@router.delete(
    "/tweets/{id}/likes",
    description="Снятие лайка",
    response_model=Result | ErrorResponse,
)
async def delete_like(
    api_key: str = Header(...),
    id: int = Path(..., gt=0, description="id твита"),
    session=Depends(get_session),
):
    try:
        delete_like_result = await DAO.like_control(
            like_id=id, api_key=api_key, method_name="remove", session=session
        )
        return delete_like_result
    except (
        ValueError,
        IntegrityError,
        NoResultFound,
    ) as ex:
        return errors(ex)


@router.post(
    "/make_user",
    description="Создание пользователя",
    response_model=UserInPost | ErrorResponse,
)
async def make_user(
    user: UserInPost,
    authorization_token: str = Header(...),
    session=Depends(get_session),
):
    try:
        if authorization_token != token:
            raise AuthorizationError()
        new_user = await DAO.add_object(User, user.dict(), session)
        return new_user
    except AuthorizationError as ex:
        return errors(ex)
    except IntegrityError as ex:
        return errors(ex, message=f"Пользователь '{user.name}' уже существует")


@router.delete(
    "/delete_user/{id}",
    description="Удаление пользователя",
    response_model=Result | ErrorResponse,
)
async def delete_user(
    authorization_token: str = Header(...),
    id: int = Path(..., gt=0, description=description_id_user),
    session=Depends(get_session),
):
    try:
        return await APIServices.delete_user(authorization_token, id, session)
    except AuthorizationError as ex:
        return errors(ex)
    except UnmappedInstanceError as ex:
        return errors(ex, message=f"Пользователь c {id = } не найден")


@router.post("/medias", description="Отправка файла", response_model=FileSendOut)
async def send_file(file: UploadFile = File(...)):
    file_in_server = await APIServices.send_file(file)
    return {"result": True} | {"media_id": file_in_server}


@router.post(
    "/tweets", response_model=SendTweetOut | ErrorResponse, description="Отправка твита"
)
async def send_tweet(
    tweets: SendTweet,
    api_key: str = Header(...),
    session=Depends(get_session),
):
    try:
        new_tweet = await APIServices.send_tweet(tweets, api_key, session)
        return {"result": True} | {"tweet_id": new_tweet.id}
    except NoResultFound as ex:
        return errors(ex, message=f"Пользователь '{api_key}' не найден")


@router.delete(
    "/tweets/{id}",
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
        await DAO.delete_tweet(api_key, id, session)
        return {"result": True}
    except NoResultFound as ex:
        response.status_code = 401
        return errors(ex, message=f"Ошибка в api_key пользователя, или id твита")
