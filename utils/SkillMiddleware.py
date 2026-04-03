from langchain.agents.middleware import ModelRequest, ModelResponse, AgentMiddleware

import os
from langchain.messages import SystemMessage
from typing import Callable
from utils.skill_loader import load_skills_from_directory
from tools.tools import load_skill, execute_sql, search_memory, read_file, write_file, edit_file, list_directory, \
    write_memory
from langchain.agents.middleware import AgentState
from typing import Any
from langgraph.runtime import Runtime
from langchain.agents import  AgentState
from langchain.agents.middleware import before_model
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langchain.messages import RemoveMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately
from config import load_config
from config.context import request_user

# 动态加载技能
skills_list = []
config = load_config()

@before_model
def trim_history_middleware(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """基于 token 限制智能修剪消息历史。"""
    messages = state["messages"]

    # 计算总 tokens
    total_tokens = count_tokens_approximately(messages)
    max_tokens = config.openai.max_tokens  # 你的 LLM 上下文限制，减去输出余量

    if total_tokens <= max_tokens:
        return None  # 无需修剪

    # 智能修剪：保留最近消息，从 human 开始，到 human/tool 结束
    trimmed = trim_messages(
        messages,
        strategy="last",  # 保留最后 N tokens
        token_counter=count_tokens_approximately,
        max_tokens=max_tokens *0.2,  # 留 20% 余量
        start_on="human",
        end_on=("human", "tool"),
    )

    # 清空历史 + 添加修剪后消息（保留关键上下文）
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *trimmed
        ]
    }

class CustomState(AgentState):
    skills_loaded:list[str]  # Track which skills have been loaded  #

class SkillMiddleware(AgentMiddleware):
    """Middleware that injects skill descriptions into the system prompt."""
    state_schema = CustomState
    # Register the load_skill tool as a class variable
    tools = [load_skill, execute_sql, search_memory, write_memory,read_file, write_file, edit_file, list_directory]
    def __init__(self):
        """Initialize and generate the skills prompt from SKILLS."""
        # Build skills prompt from the SKILLS list
        SKILLS_DIR = os.path.join(os.path.dirname(__file__), "../skills")
        
        # 获取当前用户ID
        try:
            user_id = request_user.get()
        except:
            user_id = "default"
            
        # 加载公共技能
        SKILLS = load_skills_from_directory(SKILLS_DIR)
        
        # 加载用户私有技能
        USER_SKILLS_DIR = os.path.join(os.path.dirname(__file__), f"../longtermmemory/users/{user_id}/skills")
        if os.path.exists(USER_SKILLS_DIR):
            USER_SKILLS = load_skills_from_directory(USER_SKILLS_DIR)
            # 合并技能列表，用户私有技能优先
            skills_dict = {skill["name"]: skill for skill in SKILLS}
            for user_skill in USER_SKILLS:
                skills_dict[user_skill["name"]] = user_skill
            SKILLS = list(skills_dict.values())

        for skill in SKILLS:
            skills_list.append(
                f"- **{skill['name']}**: {skill['description']}"
            )
        self.skills_prompt = "\n".join(skills_list)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Sync: Inject skill descriptions into system prompt."""
        # Build the skills addendum
        print(f"\n\n## Available Skills\n\n{self.skills_prompt}\n\n")
        skills_addendum = (
            f"\n\n## Available Skills\n\n{self.skills_prompt}\n\n"
            "Use the load_skill tool when you need detailed information "
            "about handling a specific type of request.\n"
            "Use the execute_sql tool when you want to run a SQL query "
            "against the database to get actual data."
        )

        # Append to system message content blocks
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": skills_addendum}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)
        return handler(modified_request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Async: Inject skill descriptions into system prompt."""
        # Build the skills addendum
        skills_addendum = (
            f"\n\n## Available Skills\n\n{self.skills_prompt}\n\n"
            "Use the load_skill tool when you need detailed information "
            "about handling a specific type of request.\n"
            "Use the execute_sql tool when you want to run a SQL query "
            "against the database to get actual data."
        )

        # Append to system message content blocks
        new_content = list(request.system_message.content_blocks) + [
            {"type": "text", "text": skills_addendum}
        ]
        new_system_message = SystemMessage(content=new_content)
        modified_request = request.override(system_message=new_system_message)
        return await handler(modified_request)