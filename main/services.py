import os
import shutil
from sqlalchemy.exc import NoResultFound


from main.dao import DAO
from main.exceptions import AuthorizationError
from dotenv import find_dotenv, load_dotenv

from main.models import User, Tweet
from main.schemas import SendTweet

load_dotenv(find_dotenv())
token = os.getenv("token")


class APIServices:

    @classmethod
    async def get_tweets(cls, api_key, session):
        followed_ids = await DAO.get_followed_ids(api_key, session)
        tweet_id_last = await DAO.get_last_tweet_id(
            user_id=followed_ids["user_id"], session=session
        )
        result_all = await DAO.get_tweets_ordered_from_like(
            following_ids=followed_ids["following_ids"], session=session
        )
        # ставим на первое место последний твит пользователя
        if tweet_id_last:
            for index, tweet in enumerate(result_all):
                if tweet["id"] == tweet_id_last and isinstance(result_all, list):
                    result_all.insert(0, result_all.pop(index))
                    break
        return result_all

    @classmethod
    async def delete_user(cls, authorization_token, id, session):
        if authorization_token != token:
            raise AuthorizationError()
        user_object = await DAO.search_by_fields(User, dict(id=id), session)
        await DAO.delete_object(user_object, session)
        return {"result": True}

    @classmethod
    async def send_file(cls, file):
        UPLOAD_DIR = "images/"
        root_dir = os.path.dirname(os.path.abspath(__file__))
        name = file.filename
        file_in_container = os.path.join(root_dir, UPLOAD_DIR, name)
        file_in_server = os.path.join(UPLOAD_DIR, name)
        with open(file_in_container, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return file_in_server

    @classmethod
    async def send_tweet(cls, tweets, api_key, session):
        user_id = await DAO.search_by_fields(User.id, dict(api_key=api_key), session)
        print(f"{user_id=}")
        if not user_id:
            raise NoResultFound
        data_in = cls._tweet_data(tweets)
        data_in.update({"user_maker_id": user_id})
        new_tweet = await DAO.add_object(Tweet, data_in, session)
        return new_tweet

    @staticmethod
    def _tweet_data(tweet: SendTweet) -> dict:
        """
        Функция подготовки данных для нового твита из полученного от клиента словаря SendTweet.
        """
        data_in = tweet.dict()
        data_content_list = data_in.pop("tweet_data").split("\n")
        attachments = data_in.pop("tweet_media_ids")
        for data_item in data_content_list[:]:
            if data_item.startswith("http"):
                attachments.append(data_item)
                data_content_list.remove(data_item)
        data_in["content"] = "\n".join(data_content_list)
        data_in["attachments"] = attachments
        return data_in
