import json
from typing import Optional, TypeVar, Generic
import time
import uvicorn
import asyncio
import sys
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, RedirectResponse

# 确保在导入其他模块之前设置事件循环策略
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from logger.log import SysLogger, log_user_question
from logger.log import SysLogger
from main import run_sql_agent_stream, get_session_manager
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 问数对话传入参数
class QueryRequest(BaseModel):
    type: str
    question: str
    thread_id: Optional[str] = None
    title: Optional[str] = None

# 创建新会话传入参数
class SessionCreateRequest(BaseModel):
    title: str = "新会话"

# 获取指定会话信息和删除会话传入参数
class SessionGetRequest(BaseModel):
    thread_id: str

# 更新会话标题传入参数
class SessionTitleUpdateRequest(BaseModel):
    thread_id: str
    title: str

T = TypeVar("T")
# 请求回复类
class ResponseBaseModel(BaseModel, Generic[T]):
    code:int = 200,
    messages: str = "success"
    data: Optional[T] = None

async def get_current_user_id(authorization: str = Header(None)):
    """获取当前用户ID"""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing Authorization Header")

        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid Authorization Header")

        token = authorization.split(" ")[1]
        user_id, llm_key = await get_user_info(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Token Expired")

        return user_id
    except Exception as e:
        SysLogger.exception(f"获取当前用户ID出错：{str(e)}")
        print(f"获取当前用户ID出错：{str(e)}")
        raise HTTPException(status_code=401, detail=str(e))

async def get_user_info(token: str):
    """从Redis中获取用户信息"""
    user_json = await redis_client.get(token)
    if user_json is None:
        raise HTTPException(status_code=401, detail="Token Expired")
    user_info = json.loads(user_json)
    user_id = user_info.get("user_id")
    llm_key = user_info.get("llm_key")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token Expired")
    return user_id, llm_key


# 鉴权中间件
@app.middleware("http")
async def auth_middleware(request: Request, call_next):

    if request.url.path in ["/login", "/callback", "/offlinelogin"]:
        return await call_next(request)

    print("进入鉴权中间件")
    # 优先检查Header中的Bearer Token
    access_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        access_token = auth_header.split(" ")[1]
        print(f"从Header获取token: {access_token}")

    # 如果Header中没有token，再检查Cookie
    if not access_token:
        access_token = request.cookies.get("access_token")
        print(f"从Cookie获取token: {access_token}")
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
async def chat_endpoint(req: QueryRequest, authorization: str = Header(None)):
    print(f"收到请求：{req}")
    req_type = req.type
    req_question = req.question
    thread_id = req.thread_id
    title = req.title
    # 记录请求时间戳
    request_timestamp = time.time()


    if not req.question:
        raise HTTPException(status_code=400, detail="question is required")
    try:
        if authorization:
            if authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
        else:
            token = req.cookies.get("access_token")
        user_id, llm_key = await get_user_info(token)
        if not user_id or not llm_key:
            raise HTTPException(status_code=401, detail="Token Expired")
        request_llm_key.set(llm_key)
    except Exception as e:
        print(f"获取当前用户ID出错：{str(e)}")
        raise HTTPException(status_code=401, detail="Invalid Token or Token Expired")
    if req_type == "sql":
        log_user_question(user_id, req_question)
        return StreamingResponse(
            run_sql_agent_stream(req_question, thread_id=thread_id, title=title, request_timestamp=request_timestamp),
            media_type="application/x-ndjson"
        )
    else:
        raise HTTPException(400, "type is invalid")


@app.get("/sessions")
async def list_sessions():
    """获取用户会话列表"""
    try:
        user_id = request_user.get()
        session_mgr = await get_session_manager()
        sessions = await session_mgr.get_user_sessions(user_id)
        return ResponseBaseModel(code=200, messages="success", data=sessions)
    except Exception as e:
        SysLogger.exception(f"获取用户会话列表出错：{str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 创建新会话这个接口可以不用，通过聊天接口触发的新会话产生
# @app.post("/sessions")
# async def create_session(request: SessionCreateRequest):
#     """创建新会话"""
#     try:
#         user_id = request_user.get()
#         title = request.title
#         session_mgr = await get_session_manager()
#         session = await session_mgr.create_session(user_id, title)
#
#         data = {
#             "thread_id": session.thread_id,
#             "title": session.title,
#             "created_at": session.created_at.isoformat()
#         }
#         return ResponseBaseModel(code=200, messages="success", data=data)
#         # return {"code": 200, "messages": "成功", "data": data}
#     except Exception as e:
#         print(f"创建新会话出错：{str(e)}")
#         SysLogger.exception(f"创建新会话出错：{str(e)}")
#         return HTTPException(status_code=500, detail=f"创建新会话出错：{str(e)}")




@app.post("/sessions/thread_id")
async def get_session(request: SessionGetRequest):
    """获取指定会话信息和历史记录"""
    try:
        user_id = request_user.get()
        thread_id = request.thread_id
        session_mgr = await get_session_manager()
        session = await session_mgr.get_session(thread_id)

        if session is None:
            raise HTTPException(404, "会话不存在")

        if session.user_id != user_id:
            raise HTTPException(403, "无权限访问该会话")

        # 获取会话消息历史
        messages = await session_mgr.get_session_messages(thread_id)

        return ResponseBaseModel(
            code=200,
            messages="success",
            data={
                "thread_id": session.thread_id,
                "title": session.title,
                "created_at": session.created_at.isoformat() if session.created_at else None,

                "messages": messages
            }
        )
    except Exception as e:
        print(f"获取指定会话信息出错：{str(e)}")
        SysLogger.exception(f"获取指定会话信息出错：{str(e)}")
        return HTTPException(status_code=500, detail=f"获取指定会话信息出错：{str(e)}")


@app.delete("/sessions/thread_id")
async def delete_session(request: SessionGetRequest):
    """删除会话"""
    try:
        user_id = request_user.get()
        thread_id = request.thread_id
        session_mgr = await get_session_manager()
        session = await session_mgr.get_session(thread_id)

        if session is None:
            raise HTTPException(404, "会话不存在")

        if session.user_id != user_id:
            raise HTTPException(403, "无权限删除该会话")

        await session_mgr.delete_session(thread_id)
        return ResponseBaseModel(code=200, messages="deleted", data={"thread_id": thread_id})
    except Exception as e:
        print(f"删除会话出错：{str(e)}")
        SysLogger.exception(f"删除会话出错：{str(e)}")
        return HTTPException(status_code=500, detail=f"删除会话出错：{str(e)}")


@app.put("/sessions/thread_id/title")
async def update_session_title(request: SessionTitleUpdateRequest):
    """更新会话标题"""
    try:
        user_id = request_user.get()
        thread_id = request.thread_id
        title = request.title
        session_mgr = await get_session_manager()
        session = await session_mgr.get_session(thread_id)

        if session is None:
            raise HTTPException(404, "会话不存在")

        if session.user_id != user_id:
            raise HTTPException(403, "无权限修改该会话")

        await session_mgr.update_session_title(thread_id, title)
        return ResponseBaseModel(code=200, messages="updated", data={"thread_id": thread_id, "title": title})
        # return ResponseBaseModel(code=200, messages="updated", data={"thread_id": thread_id, "title": title})
    except Exception as e:
        print(f"更新会话标题出错：{str(e)}")
        SysLogger.exception(f"更新会话标题出错：{str(e)}")
        raise HTTPException(status_code=500, detail=f"更新会话标题出错：{str(e)}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "messages": exc.detail, "data": None}
    )





if __name__ == "__main__":
    # 启动服务
    uvicorn.run(app, host="0.0.0.0", port=8023)
