from function.APIRequest import my_post
from config import load_config
from config.context import request_llm_key
from langchain_openai import ChatOpenAI
import asyncio
import threading
import httpx

config = load_config()

# 用于控制并发的信号量
_llm_semaphore = asyncio.Semaphore(10)  # 限制同时进行的LLM调用数量为10

async def get_llm_key(user_name: str):
    """
    用于获取用户的llm key
    :param user_name:用户名
    :return:该用户的llm key
    """

    try:
        url = config.llm_key.llm_key_url
        payload = {
            "name": user_name,
            "auto_create": "1"
        }

        response = await my_post(url, payload, encrypt=False)
        # 检查响应是否为httpx.Response对象
        if not hasattr(response, 'json'):
            # 如果是字符串，直接抛出异常
            if isinstance(response, str):
                raise Exception(f"API请求失败，返回字符串: {response}")
            # 如果是其他类型，尝试获取文本内容
            text_content = getattr(response, 'text', str(response))
            raise Exception(f"API请求失败，响应不是有效的JSON格式: {text_content}")
            
        try:
            response_json = response.json()
        except Exception as e:
            # 尝试获取响应的文本内容用于调试
            text_content = getattr(response, 'text', '无法获取响应文本')
            raise Exception(f"响应JSON解析失败: {str(e)}, 响应内容: {text_content}, 响应类型: {type(response)}")
            
        code = response_json.get("code")
        if code == 0:
            key = (
                response_json
                .get("data", {})
                .get("key", "")
            )
            return key

        else:
            message = response_json.get("message", "未知错误")
            raise Exception(f"获取key失败：{message}")
    except httpx.HTTPStatusError as http_error:
        # 特别处理HTTP错误
        status_code = http_error.response.status_code
        response_text = http_error.response.text
        raise Exception(f"HTTP错误 {status_code}: {response_text}")
    except Exception as e:
        raise Exception(f"获取key失败：{e}")


def get_main_llm(model: str, streaming: bool=True):
    """
    获取主流程使用的LLM对象（不缓存）
    :param model: 模型名
    :param streaming: 是否流式输出，默认是
    :return:
    """
    try:
        api_key = request_llm_key.get()
        base_url = config.openai.base_url
        
        # 直接创建新的LLM实例，不使用缓存（用于主流程）
        llm = ChatOpenAI(model=model, base_url=base_url, api_key=api_key, temperature=0.0, streaming=streaming,model_kwargs={"stream_options":{"include_usage":True}})
        return llm

    except:
        raise


def get_tool_llm(model: str, streaming: bool=False):
    """
    获取工具使用的LLM对象（不缓存）
    :param model: 模型名
    :param streaming: 是否流式输出，默认否
    :return:
    """
    try:
        api_key = request_llm_key.get()
        base_url = config.openai.base_url
        
        # 直接创建新的LLM实例，不使用缓存
        llm = ChatOpenAI(model=model, base_url=base_url, api_key=api_key, temperature=0.0, streaming=streaming)
        return llm

    except:
        raise


# 用于控制LLM调用并发的装饰器
def with_llm_semaphore(func):
    async def wrapper(*args, **kwargs):
        async with _llm_semaphore:
            return await func(*args, **kwargs)
    return wrapper