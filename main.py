import asyncio
import sys
import os
import json
from typing import AsyncGenerator
from datetime import datetime

# 第三方库导入
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

# 本地模块导入
from logger.log import SysLogger, log_user_question
from config.context import request_llm_key, request_user
from prompt.sql_agent_prompt import get_sql_system_prompt
from utils.SkillMiddleware import SkillMiddleware, trim_history_middleware
from langchain.agents.middleware import TodoListMiddleware
from config import load_config
from utils.llms import get_main_llm, get_llm_key
from utils.AgentEventProcessor import EventParser

# 在Windows上设置兼容的事件循环以支持Psycopg异步操作
if sys.platform == "win32":
    import selectors

    selector = selectors.SelectSelector()
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 加载配置
config = load_config()
os.environ["OPENAI_BASE_URL"] = config.openai.base_url

# 数据库连接配置 - 从配置文件读取
DB_URI = f"postgresql://{config.postgresqldb.user}:{config.postgresqldb.password}@{config.postgresqldb.host}:{config.postgresqldb.port}/{config.postgresqldb.database}"
connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}


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
    if sys.platform != "win32":
        # 在非Windows平台上可以进行额外的初始化
        await checkpointer.setup()

    return create_agent(
        model=model,
        system_prompt=system_prompt,
        middleware=middleware,
        checkpointer=checkpointer,
    )


# 服务端sql agent
async def run_sql_agent_stream(question: str) -> AsyncGenerator[str, None]:
    """
    生成器函数：产生流式数据，包括实时内容和最终结果。
    """
    # 服务端agent配置
    user_id = request_user.get()
    llm_key = request_llm_key.get()

    # 初始化agent配置
    model_name = config.openai.model
    system_prompt = get_sql_system_prompt()
    thread_id = f"{user_id}_{datetime.now().strftime('%Y-%m-%d')}"
    llm_config = {"recursion_limit": config.openai.recursion_limit, "configurable": {"thread_id": thread_id}}

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

    # 使用PostgreSQL作为检查点存储
    async with AsyncConnectionPool(
            conninfo=DB_URI,
            max_size=20,
            kwargs=connection_kwargs,
            timeout=60.0,
    ) as pool:
        agent = await create_agent_with_checkpointer(
            model=model,
            system_prompt=system_prompt,
            middleware=agent_config["middleware"],
            pool=pool
        )

        try:
            # # 本地运行
            # async for chunk in agent.astream(inputs, config=llm_config, stream_mode="values"):
            #     chunk["messages"][-1].pretty_print()
            # 服务器端运行
            event_parser = EventParser()
            async for chunk in agent.astream_events(inputs, config=llm_config, version="v2"):

                parser_result = event_parser.parse_event(chunk)
                if parser_result:
                    yield json.dumps(parser_result, ensure_ascii=False) + "\n"

            # 输出统计信息
            stats_result = event_parser.get_stats()
            yield json.dumps(stats_result, ensure_ascii=False) + "\n"

        # 递归达到上限报错处理
        except RecursionError as e:
            SysLogger.error(f"SQL Agent运行出错：错误类型：{type(e)}")
            SysLogger.exception(f"SQL Agent运行出错：{str(e)}")

            yield json.dumps({"type": "error",
                              "payload": {"name": "RecursionError",
                                          "output": "我在处理这个问题时遇到了一些困难，可能是任务步骤过于复杂导致的。你可以提供更多细节继续问我 😊"}},
                             ensure_ascii=False) + "\n"

        except Exception as e:
            err_msg = str(e)
            SysLogger.exception(f"SQL Agent运行出错：{err_msg}")
            cn_err_msg = ""
            if "No generations found in stream" in err_msg:
                cn_err_msg = "模型暂未返回内容，请稍后再试"

                yield json.dumps({"type": "error",
                                  "payload": {"name": "No generations found in stream",
                                              "output": f"{cn_err_msg}"}}, ensure_ascii=False) + "\n"
            else:
                yield json.dumps({"type": "error",
                                  "payload": {"name": "Exception",
                                              "output": f"{err_msg}"}}, ensure_ascii=False) + "\n"


# Example usage
if __name__ == "__main__":
    # 或者通过Web流式函数运行
    async def main():
        # 本地运行环境模型配置,服务器端需要注释掉
        user_id = "jiangjunhua"
        request_user.set(user_id)
        llm_key = await get_llm_key(user_id)
        request_llm_key.set(llm_key)
        question = '全市场保有量 '
        async for chunk in run_sql_agent_stream(question):
            print(chunk)


    asyncio.run(main())