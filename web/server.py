import asyncio
import os
import httpx
import json
# from dotenv import load_dotenv
from contextlib import asynccontextmanager
import time
import uvicorn
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from main import run_sql_agent_stream
from pydantic import BaseModel
from config.context import request_llm_key, request_user
from config import load_config
from utils.redis_client import redis_client
from web.oauth_iam import oauth_router

config = load_config()

app = FastAPI()
app.include_router(oauth_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法 (GET, POST, OPTIONS 等)
    allow_headers=["*"],  # 允许所有 Header
)



# 问数对话传入参数
class QueryRequest(BaseModel):
    type: str
    question: str



# 鉴权中间件
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    print("进入鉴权中间件")
    if request.url.path in ["/login", "/callback"]:
        return await call_next(request)

    # 从cookie中获取token
    access_token = request.cookies.get("access_token")
    redirect_url = config.oauth.redirect_url.rstrip("/")
    print(f"鉴权中间件获取token==={access_token}")
    # auth_header = request.headers.get("Authorization")
    # if not auth_header:
    #     return HTTPException(status_code=401, detail="Missing Auth Header")
    #
    # access_token = auth_header.replace("Bearer ", "")
    if not access_token:
        return RedirectResponse(redirect_url + "/login", status_code=302)

    user_json = await redis_client.get(access_token)
    if not user_json:
        return RedirectResponse(redirect_url + "/login", status_code=302)

    # 重置登录时间
    await redis_client.expire(access_token, 86400)
    print(f"重置登录时间")
    user_info = json.loads(user_json)

    # 写入context
    request_user.set(user_info["user_id"])
    request_llm_key.set(user_info["llm_key"])

    response = await call_next(request)
    return response


@app.post("/chat/stream")
async def chat_endpoint(req: QueryRequest):
    print(f"收到请求：{req}")
    req_type = req.type # 类型
    req_question = req.question # 问题



    if not req.question:
        return HTTPException(400, "question is required")

    # 请求头
    response_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-ndjson; charset=utf-8",
    }

    # text2sql入口
    if req_type == "sql":
        return StreamingResponse(
            run_sql_agent_stream(req_question),
            media_type="application/x-ndjson"
        )
    else:
        return HTTPException(400, "type is invalid")




if __name__ == "__main__":
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8023)