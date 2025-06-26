import os
import shutil

import pytest

from main.app import logger, token


@pytest.mark.asyncio
async def test_get_tweets(async_client):
    response = await async_client.get("api/tweets", headers={"api-key": "test"})
    tweets_json = response.json()
    logger.info(tweets_json)
    assert tweets_json == {
        "result": True,
        "tweets": [
            {
                "id": 1,
                "content": "Привет всем",
                "attachments": ["images/image.jpg"],
                "author": {"id": 1, "name": "Вася"},
                "likes": [],
            },
            {
                "id": 2,
                "content": "Кто тут?",
                "attachments": ["images/image_2.png"],
                "author": {"id": 2, "name": "Петя"},
                "likes": [{"id": 1, "name": "Вася"}],
            },
        ],
    }


@pytest.mark.asyncio
async def test_get_tweets_fail(async_client):
    response = await async_client.get("api/tweets", headers={"api-key": "qwerty"})
    tweets_json = response.json()
    logger.info(tweets_json)
    assert not tweets_json["result"]


@pytest.mark.asyncio
async def test_get_profile(async_client):
    for id, name in {1: "Вася", 2: "Петя", 3: "Катя"}.items():
        response = await async_client.get(f"/api/users/{id}")
        user_json = response.json()
        logger.info(user_json)
        user_name = user_json["user"]["name"]
        assert response.status_code == 200
        assert name == user_name


@pytest.mark.asyncio
async def test_get_profile_fail(async_client):
    response = await async_client.get(f"/api/users/g")
    user_json = response.json()
    logger.info(user_json)
    assert not user_json["result"]


@pytest.mark.asyncio
async def test_get_my_profile(async_client):
    for apy_key, name in {"test": "Вася", "asd": "Петя", "zxc": "Катя"}.items():
        response = await async_client.get(
            f"/api/users/me", headers={"api-key": apy_key}
        )
        user_json = response.json()
        logger.info(user_json)
        user_name = user_json["user"]["name"]
        assert response.status_code == 200
        assert name == user_name


@pytest.mark.asyncio
async def test_get_my_profile_fail(async_client):
    for apy_key, name in {"testa": "Вася", "as": "Петя", "zc": "Катя"}.items():
        response = await async_client.get(
            f"/api/users/me", headers={"api-key": apy_key}
        )
        user_json = response.json()
        logger.info(user_json)
        assert not user_json["result"]


@pytest.mark.asyncio
async def test_follow(async_client):
    response = await async_client.post(
        "/api/users/1/follow", headers={"api-key": "asd"}
    )
    follow_json = response.json()
    logger.info(follow_json)
    assert follow_json["result"]


@pytest.mark.asyncio
async def test_follow_fail(async_client):
    for api_key, id in (("test", 1), ("asd ", 2), ("test", 2)):
        response = await async_client.post(
            f"/api/users/{id}/follow", headers={"api-key": f"{api_key}"}
        )
        follow_json = response.json()
        logger.info(follow_json)
        assert not follow_json["result"]


@pytest.mark.asyncio
async def test_unfollow(async_client):
    response = await async_client.delete(
        "/api/users/2/follow", headers={"api-key": "test"}
    )
    unfollow_json = response.json()
    logger.info(unfollow_json)
    assert unfollow_json["result"]


@pytest.mark.asyncio
async def test_unfollow_fail(async_client):
    for api_key, id in (("test ", 2), ("asd", 2), ("test", "2a")):
        response = await async_client.delete(
            f"/api/users/{id}/follow", headers={"api-key": f"{api_key}"}
        )
        unfollow_json = response.json()
        logger.info(unfollow_json)
        assert not unfollow_json["result"]


@pytest.mark.asyncio
async def test_like(async_client):
    response = await async_client.post(
        "/api/tweets/1/likes", headers={"api-key": "test"}
    )
    like_json = response.json()
    logger.info(like_json)
    assert like_json["result"]


@pytest.mark.asyncio
async def test_like_fail(async_client):
    for api_key, id in (("test", 2), ("asd", "a"), ("test", 11)):
        response = await async_client.post(
            f"/api/tweets/{id}/likes", headers={"api-key": f"{api_key}"}
        )
        like_json = response.json()
        logger.info(like_json)
        assert not like_json["result"]


@pytest.mark.asyncio
async def test_unlike(async_client):
    response = await async_client.post(
        "/api/tweets/2/likes", headers={"api-key": "test"}
    )
    unlike_json = response.json()
    logger.info(unlike_json)
    assert not unlike_json["result"]


@pytest.mark.asyncio
async def test_unlike_fail(async_client):
    for api_key, id in (("test", 1), ("asd", 1)):
        response = await async_client.post(
            f"/api/tweets/{id}/likes", headers={"api-key": f"{api_key}"}
        )
        unlike_json = response.json()
        logger.info(unlike_json)
        assert unlike_json["result"]


@pytest.mark.asyncio
async def test_make_user(async_client):
    data = {"api_key": "aabbcc11", "name": "Лёша"}
    response = await async_client.post(
        "/api/make_user", headers={"authorization-token": token}, json=data
    )
    make_user_json = response.json()
    logger.info(make_user_json)
    assert {"api_key": "aabbcc11", "name": "Лёша"}


@pytest.mark.asyncio
async def test_make_user_fail(async_client):
    data_1 = ({"api_key": "ttttt", "name": "Дима"}, "FFkhd25JK")
    data_2 = ({"api_key": "test", "name": "Лёша"}, token)
    for data, _token in (data_1, data_2):
        response = await async_client.post(
            "/api/make_user", headers={"authorization-token": f"{_token}"}, json=data
        )
        make_user_fail_json = response.json()
        logger.info(make_user_fail_json)
        assert not make_user_fail_json["result"]


@pytest.mark.asyncio
async def test_delete_user(async_client):
    response = await async_client.delete(
        "/api/delete_user/1", headers={"authorization-token": token}
    )
    delete_user = response.json()
    logger.info(delete_user)
    assert delete_user["result"]


@pytest.mark.asyncio
async def test_delete_user_fail(async_client):
    response = await async_client.delete(
        "/api/delete_user/11", headers={"authorization-token": token}
    )
    delete_user_fail = response.json()
    logger.info(delete_user_fail)
    assert not delete_user_fail["result"]


@pytest.mark.asyncio
async def test_send_file(async_client):
    file_content = b"test file content"
    files = {"file": ("../../tests/images/test_file.txt", file_content, "text/plain")}
    os.makedirs("images")
    response = await async_client.post("/api/medias", files=files)
    send_file = response.json()
    logger.info(send_file)
    shutil.rmtree("images")
    assert {"result": True, "media_id": "images/test_file.txt"}


@pytest.mark.asyncio
async def test_send_tweet(async_client):
    data = {
        "tweet_data": "Очень интересно! https://avatars.mds.yandex.net/get-altay/11072941/2a0000018c001377788525af99bf0e060770/orig",
        "tweet_media_ids": ["file_1.jpg", "file_2.png"],
    }
    response = await async_client.post(
        "/api/tweets", json=data, headers={"api-key": "asd"}
    )
    send_tweet = response.json()
    logger.info(send_tweet)
    assert {"result": True, "tweet_id": 3}


@pytest.mark.asyncio
async def test_send_tweet_fail(async_client):
    data_1 = ({"tweet_media_ids": []}, "asd")
    data_2 = ({"tweet_data": "добрый день", "tweet_media_ids": []}, "aaa")
    for data, api_key in (data_1, data_2):
        response = await async_client.post(
            "/api/tweets", json=data, headers={"api-key": api_key}
        )
        send_tweet_fail = response.json()
        logger.info(send_tweet_fail)
        assert not send_tweet_fail["result"]


@pytest.mark.asyncio
async def test_delete_tweet(async_client):
    for tweet_id, api_key in {1: "test", 2: "asd"}.items():
        response = await async_client.delete(
            f"/api/tweets/{tweet_id}", headers={"api-key": api_key}
        )
        delete_tweet = response.json()
        logger.info(delete_tweet)
        assert delete_tweet["result"]


@pytest.mark.asyncio
async def test_delete_tweet_fail(async_client):
    for tweet_id, api_key in {2: "test", 1: "asd"}.items():
        response = await async_client.delete(
            f"/api/tweets/{tweet_id}", headers={"api-key": api_key}
        )
        delete_tweet = response.json()
        logger.info(delete_tweet)
        assert not delete_tweet["result"]
