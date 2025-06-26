from typing import List, Optional

from fastapi.openapi import utils
from pydantic import BaseModel, Field

# переопределяем схему валидации ошибок в swagger
utils.validation_error_response_definition = {
    "title": "HTTPValidationError",
    "type": "object",
    "properties": {
        "result": {"title": "Success", "type": "boolean", "default": False},
        "error_type": {"title": "Message", "type": "string"},
        "error_message": {"title": "Message", "type": "string"},
    },
}


class BaseUser(BaseModel):
    api_key: str = Field(..., min_length=3, description="api-ключ пользователя")
    name: str = Field(..., min_length=3, description="Имя пользователя")


class UserInPost(BaseUser): ...


class FileSendOut(BaseModel):
    result: bool
    media_id: str


class SendTweet(BaseModel):
    tweet_data: str = Field(..., min_length=1, description="Текст сообщения")
    tweet_media_ids: Optional[List] = Field(
        default=[], description="Список путей к медиа-файлу"
    )


class SendTweetOut(BaseModel):
    result: bool
    tweet_id: int = Field(..., gt=0)


class Author(BaseModel):
    id: int = Field(..., gt=0)
    name: str


class Like(BaseModel):
    user_id: int = Field(..., gt=0)
    name: str


class Followers(Author): ...


class Following(Author): ...


class UserProfile(Author):
    followers: List[Followers]
    following: List[Following]


class GetUserProfile(BaseModel):
    result: bool = True
    user: UserProfile


class Tweet(BaseModel):
    id: int = Field(..., gt=0)
    content: str
    attachments: List[str]
    author: Author
    likes: List[Like]


class GetTweets(BaseModel):
    result: bool = True
    tweets: List[Tweet]


class Result(BaseModel):
    result: bool = True


class ErrorResponse(BaseModel):
    result: bool = False
    error_type: str
    error_message: str
