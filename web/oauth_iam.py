import os
import time
import secrets
import httpx
from urllib.parse import quote
from fastapi import APIRouter, Response, HTTPException, Request
from starlette.responses import JSONResponse, RedirectResponse
from config import load_config
from utils.redis_client import redis_client
import json
from pathlib import Path
from utils.llms import get_llm_key
config = load_config()

# 创建路由器
oauth_router = APIRouter()

# 获取配置
client_id = config.oauth.client_id
client_secret = config.oauth.client_secret
iam_auth_url = config.oauth.auth_url
#redirect_url = config.oauth.redirect_url.rstrip("/")
redirect_url = config.oauth.redirect_url
access_token_url = config.oauth.access_token_url
profile_url = config.oauth.profile_url


# 登录(用于获取code，然后自动重定向到/callback)
@oauth_router.get("/login")
async def iam_login():
    try:
        print("进入login事件")
        # 验证必要配置
        if not all([iam_auth_url, client_id, redirect_url]):
            print("缺少必要配置")
            raise HTTPException(status_code=500, detail="Missing IAM configuration")

        redirect_url_encoded = quote(redirect_url + "/callback", safe="") # 添加/callback 登录成功自动跳转到相应事件获取token和profile
        auth_url = (
            f"{iam_auth_url}?"
            f"client_id={client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_url_encoded}"
        )
        print(f"login事件auth_url==={auth_url}")
        return RedirectResponse(auth_url, status_code=302)

    except Exception as e:
        return HTTPException(status_code=500, detail=f"Login Error: {str(e)}")


# IAM认证(用于获取token和profile)
@oauth_router.get("/callback")
async def callback(code: str):
    try:
        print("进入callback事件")
        if not code:
            print("code is required")
            return JSONResponse({"message": "code is required"}, status_code=401)
        # 验证必要配置
        if not all([client_id, client_secret, access_token_url, profile_url, redirect_url]):
            print("缺少必要配置")
            raise HTTPException(status_code=500, detail="Missing OAuth configuration")
        timestamp = int(time.time() * 1000)
        # 利用code获取token
        redirect_url_encoded = quote(redirect_url, safe="")
        full_access_token_url = f"{access_token_url}?grant_type=authorization_code&oauth_timestamp={timestamp}&client_id={client_id}&client_secret={client_secret}&code={code}&redirect_uri={redirect_url_encoded}"
        print(f"callback事件full_access_token_url==={full_access_token_url}")
        async with httpx.AsyncClient(timeout=30) as client:
            token_response = await client.post(url=full_access_token_url)

            if token_response.status_code != 200:
                error_msg = f"Token request failed: {token_response.status_code}"
                return JSONResponse({"message": error_msg}, status_code=401)

            token_data = token_response.json()

        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in")
        refresh_token = token_data.get("refresh_token")  # 刷新令牌，不一定有

        if not all([access_token, expires_in]):
            return JSONResponse({"message": "Failed to get access token"}, status_code=401)

        full_profile_url = f"{profile_url}?access_token={access_token}"
        async with httpx.AsyncClient(timeout=30) as client:
            profile_response = await client.get(url=full_profile_url)

            if profile_response.status_code != 200:
                error_msg = f"Profile request failed: {profile_response.status_code}"
                return JSONResponse({"message": error_msg}, status_code=401)

        profile_data = profile_response.json()

        user_id = profile_data.get("id")
        user_name = profile_data.get("attributes").get("user_name")
        llm_key = await get_llm_key(user_id)

        # 重定向
        response = RedirectResponse(url=redirect_url, status_code=302)

        # 缓存用户信息到redis
        redis_user_info = {
            "user_id": user_id,
            "user_name": user_name,
            "llm_key": llm_key,
            "refresh_token": refresh_token
        }
        await redis_client.setex(
            name=access_token,
            time=86400,
            value=json.dumps(redis_user_info)
        )

        # 这里存到cookie中备用，可以根据实际情况调整
        is_https = redirect_url.startswith("https")

        # 写入session_id
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=expires_in,
            secure=is_https,
            httponly=False,
            samesite="lax" if not is_https else "none"
        )

        return response
    except Exception as e:
        return JSONResponse({"message": f"Callback Error: {str(e)}"}, status_code=500)






