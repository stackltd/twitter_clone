from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import selectinload

from main.models import Tweet, User
from main.schemas import SendTweet

result_true = {"result": True}


def errors(ex) -> dict:
    """
    Возвращает словарь с результатом исключения
    :param ex:
    :return:
    """
    return {
        "result": False,
        "error_type": type(ex).__name__,
        "error_message": ex.args[0],
    }


def tweet_data(tweet: SendTweet) -> dict:
    """
    Функция подготовки данных для нового твита из полученного от клиента словаря SendTweet.
    """
    data_in = tweet.dict()
    data_content_list = data_in.pop("tweet_data").split()
    attachments = data_in.pop("tweet_media_ids")
    for data_item in data_content_list[:]:
        if data_item.startswith("http"):
            attachments.append(data_item)
            data_content_list.remove(data_item)
    data_in["content"] = " ".join(data_content_list)
    data_in["attachments"] = attachments
    return data_in


async def seed_data_statement(session):
    """
    Функция предоставляет команды создания начальных данных для вновь созданных таблиц базы данных.
    """
    user_data = [
        User(api_key="test", name="Вася"),
        User(api_key="asd", name="Петя"),
        User(api_key="zxc", name="Катя"),
    ]
    session.add_all(user_data)

    # создание твитов
    tweet_1 = Tweet(
        user_maker_id=1, content="Привет всем", attachments=["images/image.jpg"]
    )
    tweet_2 = Tweet(
        user_maker_id=2, content="Кто тут?", attachments=["images/image_2.png"]
    )
    session.add_all([tweet_1, tweet_2])

    # подписка одного пользователя на другого
    user_follower_object = await session.execute(
        select(User)
        .options(selectinload(User.following))
        .options(selectinload(User.followers))
        .filter_by(id=1)
    )
    user_follower = user_follower_object.scalar_one()
    user_following_object = await session.execute(select(User).filter_by(id=2))
    user_following = user_following_object.scalar_one()
    user_follower.following.append(user_following)

    # лайк твита пользователем
    tweet_object = await session.execute(
        select(Tweet).options(selectinload(Tweet.users_who_liked)).filter_by(id=2)
    )
    tweet = tweet_object.scalar_one()
    user_object = await session.execute(select(User).filter_by(api_key="test"))
    user = user_object.scalar_one()
    tweet.users_who_liked.append(user)


async def get_user(field, field_value, session) -> User:
    """
    Функция возвращает user, присоединяя к нему данные от таблицы user_follow
    """
    async with session.begin():
        user_object = await session.execute(
            select(User)
            .options(selectinload(User.following))
            .options(selectinload(User.followers))
            .filter_by(**{field: field_value})
        )
        return user_object.scalar_one()


async def get_profile(field, field_value, response, session) -> dict:
    """
    Функция возвращает данные профиля пользователя
    :param field:
    :param field_value:
    :return:
    """
    try:
        user = await get_user(field, field_value, session)
        async with session.begin():
            followers = [follower.to_json() for follower in user.followers]
            following = [followed.to_json() for followed in user.following]

            user_dict = user.to_json()
            user_out = result_true | {
                "user": user_dict | {"followers": followers} | {"following": following},
            }
            await session.commit()
        return user_out

    except (AttributeError, NoResultFound) as ex:
        response.status_code = 401
        return errors(ex)


async def follow_control(id, api_key, method_name, session) -> dict:
    """
    Функция управления подпиской
    :param id:
    :param api_key:
    :param method_name:
    :return:
    """
    try:
        user_follower = await get_user(
            field="api_key", field_value=api_key, session=session
        )
        async with session.begin():
            # Получаем user_following
            user_following_object = await session.execute(select(User).filter_by(id=id))
            user_following = user_following_object.scalar_one()

            method = getattr(user_follower.following, method_name)
            method(user_following)
            return result_true
    except (
        ValueError,
        IntegrityError,
        NoResultFound,
    ) as ex:
        return errors(ex)


async def like_control(like_id, api_key, method_name, session) -> dict:
    """
    Функция управления лайками
    :param like_id:
    :param api_key:
    :param method_name:
    :return:
    """
    try:
        async with session.begin():
            # Получаем твит
            tweet_object = await session.execute(
                select(Tweet)
                .options(selectinload(Tweet.users_who_liked))
                .filter_by(id=like_id)
            )
            tweet = tweet_object.scalar_one()
            # Получаем user
            user_object = await session.execute(select(User).filter_by(api_key=api_key))
            user = user_object.scalar_one()
            # применяем нужный метод к объекту tweet.users_who_liked (remove, или append)
            method = getattr(tweet.users_who_liked, method_name)
            method(user)
            return result_true
    except (
        ValueError,
        IntegrityError,
        NoResultFound,
    ) as ex:
        return errors(ex)


async def get_followed_ids(api_key, session) -> dict:
    """
    Функция возвращает словарь со списком id зафолловленных и id текущего пользователя
    """
    async with session.begin():
        user_object = await session.execute(
            select(User)
            .options(selectinload(User.following))
            .filter_by(api_key=api_key)
        )
        user = user_object.scalar_one_or_none()
        user_id = user.id

        following_ids = [followed.id for followed in user.following]
        following_ids.append(user_id)
        return {"user_id": user_id, "following_ids": following_ids}


async def get_last_tweet_id(user_id, session) -> int | None | dict:
    """
    Функция возвращает id последнего твита пользователя
    """
    try:
        async with session.begin():
            # получаем id последнего твита пользователя
            tweet_id_object = await session.execute(
                select(Tweet.id)
                .join(Tweet.user)
                .where(Tweet.user.has(id=user_id))
                .order_by(Tweet.id.desc())
            )
            tweet_ids = tweet_id_object.scalars().all()
            tweet_id_last = tweet_ids[0] if tweet_ids else None
            return tweet_id_last
    except AttributeError as ex:
        return errors(ex)


async def get_tweets_ordered_from_like(following_ids, session) -> list | dict:
    """
    Функция возвращает список твитов своих и зафолловленных, отсортированных по популярности
    """
    try:
        async with session.begin():
            # получение твитов своих и зафолловленных, отсортированных по популярности
            tweets_object = await session.execute(
                select(Tweet)  # noqa: WPS221
                .options(selectinload(Tweet.user))
                .options(selectinload(Tweet.users_who_liked))
                .where(Tweet.user_maker_id.in_(following_ids))
                .outerjoin(Tweet.users_who_liked)  # left join по связи many-to-many
                .group_by(Tweet.id)
                .order_by(func.count(User.id).desc())  # сортировка по количеству лайков
            )
            result_list = tweets_object.scalars().all()
            result_all = [
                (
                    {
                        tweet_key: tweet_value
                        for tweet_key, tweet_value in tweet.to_json().items()
                    }
                    | {"likes": [{"user_id": user.id, "name": user.name} for user in tweet.users_who_liked]}
                    | {"author": {"id": tweet.user.id, "name": tweet.user.name}}
                )
                for tweet in result_list
            ]
        return result_all
    except AttributeError as ex:
        return errors(ex)
