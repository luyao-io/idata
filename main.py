# Windows下设置全局事件循环策略，确保psycopg正常工作
import asyncio
import sys
from datetime import datetime
if sys.platform == "win32":
    import selectors

    selector = selectors.SelectSelector()
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import json
from typing import AsyncGenerator, Optional
import os
# 第三方库导入
from langchain.agents import create_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
import asyncpg

# 本地模块导入
from logger.log import SysLogger, log_user_question
from config.context import request_llm_key, request_user
from prompt.sql_agent_prompt import get_sql_system_prompt
from utils.SkillMiddleware import SkillMiddleware, trim_history_middleware
from langchain.agents.middleware import TodoListMiddleware
from config import load_config
from utils.llms import get_main_llm, get_llm_key
from utils.AgentEventProcessor import EventParser
from session.manager import SessionManager, create_session_manager

# 加载配置
config = load_config()
os.environ["OPENAI_BASE_URL"] = config.openai.base_url

# 数据库连接配置 - 从配置文件读取
DB_URI = f"postgresql://{config.postgresqldb.user}:{config.postgresqldb.password}@{config.postgresqldb.host}:{config.postgresqldb.port}/{config.postgresqldb.database}"
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}

# 全局连接池
_connection_pool: Optional[AsyncConnectionPool] = None


async def get_connection_pool() -> AsyncConnectionPool:
    """获取全局连接池实例"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = AsyncConnectionPool(
            conninfo=DB_URI,
            max_size=20,
            kwargs=connection_kwargs,
            timeout=60.0
        )
        # 显式打开连接池
        await _connection_pool.open()
    return _connection_pool


# 全局会话管理器
_session_manager: Optional[SessionManager] = None


async def get_session_manager() -> SessionManager:
    """Get or create the global session manager."""
    global _session_manager
    if _session_manager is None:
        db_pool = asyncpg.create_pool(
            host=config.postgresqldb.host,
            port=int(config.postgresqldb.port),
            user=config.postgresqldb.user,
            password=config.postgresqldb.password,
            database=config.postgresqldb.database,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        # 确保连接池已初始化
        await db_pool
        _session_manager = await create_session_manager(db_pool)
    return _session_manager


def get_agent_config():
    """
    获取agent通用配置
    """
    return {
        "middleware": [SkillMiddleware(), TodoListMiddleware(), trim_history_middleware],
    }


async def create_agent_with_checkpointer(model, system_prompt, middleware, pool):
    """
    创建带检查点的agent
    """
    checkpointer = AsyncPostgresSaver(pool)
    # 尝试设置检查点存储，即使在Windows上也尝试，仅在特定错误时处理
    try:
        await checkpointer.setup()
    except Exception as e:
        SysLogger.warning(f"Checkpointer setup failed: {e}")
        # 可以继续运行，但没有检查点功能

    return create_agent(
        model=model,
        system_prompt=system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )


async def run_sql_agent_stream(
        question: str,
        thread_id: Optional[str] = None,
        title: Optional[str] = None,
        request_timestamp: Optional[float] = None
) -> AsyncGenerator[str, None]:
    """
    生成器函数：产生流式数据，包括实时内容和最终结果。

    Args:
        question: 用户问题
        thread_id: 会话ID，不传则创建新会话
    """
    # Windows下确保使用正确的事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # 在流式输出的开头返回时间戳
    if request_timestamp is not None:
        yield json.dumps({
            "type": "timestamp",
            "payload": {
                "request_timestamp": request_timestamp
            }
        }, ensure_ascii=False) + "\n"

    user_id = request_user.get()
    llm_key = request_llm_key.get()

    session_mgr = await get_session_manager()

    if thread_id is None:
        title='新会话'
        session_meta = await session_mgr.create_session(user_id, title )
        thread_id = session_meta.thread_id
        # 在用户发送第一条消息时保存会话到数据库
        await session_mgr.save_session_if_needed(thread_id, user_id, title )
    else:
        await session_mgr.touch_session(thread_id)

    # 生成统一格式的时间戳
    current_time = datetime.now()
    current_time_iso = current_time.isoformat()

    # 保存用户消息到数据库（使用datetime对象保存到数据库）
    await session_mgr.save_message(thread_id, "user", {
        "type": "text",
        "payload": {
            "content": question
        }
    }, request_timestamp=current_time)

    model_name = config.openai.model
    system_prompt = get_sql_system_prompt()
    llm_config = {
        "recursion_limit": config.openai.recursion_limit,
        "configurable": {"thread_id": thread_id}
    }

    # 使用get_main_llm函数获取主流程LLM实例
    model = get_main_llm(model=model_name, streaming=True)

    # 初始化信息
    inputs = {
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ]
    }

    agent_config = get_agent_config()

    # 使用PostgreSQL作为检查点存储，采用上下文管理器方式
    async with AsyncConnectionPool(
            conninfo=DB_URI,
            max_size=20,
            kwargs=connection_kwargs,
            timeout=60.0
    ) as pool:
        agent = await create_agent_with_checkpointer(
            model=model,
            system_prompt=system_prompt,
            middleware=agent_config["middleware"],
            pool=pool
        )
        # 收集同一轮assistant响应的所有消息
        current_assistant_response = []
        try:
            # 本地运行
            async for chunk in agent.astream(inputs, config=llm_config, stream_mode="values"):
                chunk["messages"][-1].pretty_print()
            # 服务器端运行
            event_parser = EventParser()

            
            async for chunk in agent.astream_events(inputs, config=llm_config, version="v2"):

                parser_result = event_parser.parse_event(chunk)
                if parser_result:
                    yield json.dumps(parser_result, ensure_ascii=False) + "\n"

                    # 获取消息类型
                    current_assistant_response.append(parser_result)

            # 只在流处理结束时输出最终统计信息
            stats_result = event_parser.get_stats()
            # 将统计信息保存到数据库
            await session_mgr.save_message(thread_id, "assistant", content=current_assistant_response,request_timestamp=current_time,
                                           token_info=stats_result)
            yield json.dumps(stats_result, ensure_ascii=False) + "\n"

        # 递归达到上限报错处理
        except RecursionError as e:
            SysLogger.error(f"SQL Agent运行出错：错误类型：{type(e)}")
            SysLogger.exception(f"SQL Agent运行出错：{str(e)}")

            need_continue= json.dumps({
                "type": "need_continue",
                "payload": {
                    "name": "RecursionError",
                    "output": "任务步骤过于复杂，我需要你提供更多细节来继续这个问题。",
                    "run_id": thread_id,
                    "thread_id": thread_id,
                    "suggestion": "请提供更多具体信息，例如：具体日期范围、特定客户类型、查询维度等"
                }
            }, ensure_ascii=False)
            yield need_continue + "\n"
            # 保存错误信息到数据库
            await session_mgr.save_message(thread_id, "assistant", content=current_assistant_response,
                                         request_timestamp=current_time,
                                         error_info=need_continue)
        except Exception as e:
            err_msg = str(e)
            SysLogger.exception(f"SQL Agent运行出错：{err_msg}")
            if "No generations found in stream" in err_msg:

                cn_err_msg= {"type": "error",
                                  "payload": {"name": "No generations found in stream",
                                              "output": f"{err_msg}"}}

                yield json.dumps(cn_err_msg, ensure_ascii=False) + "\n"

            else:
                cn_err_msg=  {"type": "error",
                                  "payload": {"name": "Exception",
                                              "output": f"{err_msg}"}}
                yield json.dumps(cn_err_msg, ensure_ascii=False) + "\n"
            # 保存错误信息到数据库
            await session_mgr.save_message(thread_id, "assistant", content=current_assistant_response,
                                               request_timestamp=current_time,
                                               error_info=cn_err_msg)


# Example usage
if __name__ == "__main__":
    async def main():
        user_id = "baoyaoyao"
        request_user.set(user_id)
        llm_key = await get_llm_key(user_id)
        request_llm_key.set(llm_key)
        question = '''SELECT 
    r.prod_cd as 产品代码,
    r.prod_abbr as 产品简称,
    r.tm_rng as 时间范围,
    r.tm_rng_nmrc as 时间范围数值,
    TO_DATE(m.f_info_setupdate, 'YYYYMMDD') as 成立日期,
    DATEDIFF('year', TO_DATE(m.f_info_setupdate, 'YYYYMMDD'), sttc_dt) as 距统计日期运作年数,
    r.sttc_dt as 统计日期,
    r.yld as 收益率,
    r.rtng_orgn as 机构,
    CASE 
        WHEN r.yld IS NULL AND DATEDIFF('year', TO_DATE(m.f_info_setupdate, 'YYYYMMDD'), CURRENT_DATE) >= r.tm_rng_nmrc 
        THEN '异常：运作时间足够但收益率为空' 
        ELSE '正常' 
    END as 数据状态
FROM dev_ads_opna.t_prod_prfr_rnk r
JOIN dev_dl_ods_info.s081_pdata_chinamutualfunddescription m 
    ON substr(r.prod_cd, 1, 6) = substr(m.f_info_windcode, 1, 6)
WHERE r.yld IS NULL
and sttc_dt- TO_DATE(m.f_info_setupdate, 'YYYYMMDD') >=365*DATEDIFF('year', TO_DATE(m.f_info_setupdate, 'YYYYMMDD'), sttc_dt)
AND DATEDIFF('year', TO_DATE(m.f_info_setupdate, 'YYYYMMDD'), sttc_dt) >= r.tm_rng_nmrc,检查一下这个数据dqc是否能准确检查数据质量，完整吗'''
        # 不传 thread_id，创建新会话
        async for chunk in run_sql_agent_stream(question):
            print(chunk)

        # 或者传入 thread_id 继续某个会话
        # async for chunk in run_sql_agent_stream(question, thread_id="fengyuqing_a1b2c3d4e5f6"):
        #     print(chunk)


    asyncio.run(main())