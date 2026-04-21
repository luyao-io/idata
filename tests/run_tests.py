import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import httpx

url="http://10.4.41.146:1000/v1"
async def test_llm_basic():
    """测试基本的 LLM 调用"""
    print("=" * 50)
    print("测试 1: 基本 LLM 调用")
    print("=" * 50)

    llm = ChatOpenAI(
        model="Qwen3-Coder",
        temperature=0.5,
        # base_url="http://msgw-aibot-dev.fullgoal.com.cn/v1",
        base_url=url,
        api_key="sk-JVo8j1Qjpr4LdQ0bA1C7C5AcA129425fA297F67cC29b730c",
        max_tokens=1000,
        streaming=True
    )

    messages = [
        HumanMessage(content="你好，请介绍一下自己")
    ]

    try:
        async for chunk in llm.astream(messages):
            print(f"Chunk: {chunk.content}", end="", flush=True)
        print("\n测试 1 通过!")
    except Exception as e:
        print(f"\n测试 1 失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def test_llm_with_system_message():
    """测试带 system message 的调用"""
    print("\n" + "=" * 50)
    print("测试 2: 带 system message 的调用")
    print("=" * 50)

    llm = ChatOpenAI(
        model="Qwen3-Coder",
        temperature=0.5,
        base_url=url,
        api_key="sk-JVo8j1Qjpr4LdQ0bA1C7C5AcA129425fA297F67cC29b730c",
        max_tokens=1000,
        streaming=True
    )

    messages = [
        SystemMessage(content="你是一个有帮助的AI助手"),
        HumanMessage(content="你好")
    ]

    try:
        async for chunk in llm.astream(messages):
            print(f"Chunk: {chunk.content}", end="", flush=True)
        print("\n测试 2 通过!")
    except Exception as e:
        print(f"\n测试 2 失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def test_llm_non_streaming():
    """测试非流式调用"""
    print("\n" + "=" * 50)
    print("测试 3: 非流式调用")
    print("=" * 50)

    llm = ChatOpenAI(
        model="Qwen3-Coder",
        temperature=0.5,
        base_url=url,
        api_key="sk-JVo8j1Qjpr4LdQ0bA1C7C5AcA129425fA297F67cC29b730c",
        max_tokens=1000,
        streaming=False
    )

    messages = [
        HumanMessage(content="你好，请介绍一下自己")
    ]

    try:
        response = await llm.ainvoke(messages)
        print(f"Response: {response.content}")
        print("测试 3 通过!")
    except Exception as e:
        print(f"\n测试 3 失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def test_direct_api_call():
    """直接测试 API 调用，查看原始响应"""
    print("\n" + "=" * 50)
    print("测试 4: 直接 API 调用调试")
    print("=" * 50)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        base_url=url,
        api_key="sk-JVo8j1Qjpr4LdQ0bA1C7C5AcA129425fA297F67cC29b730c",
        max_retries=0,
        timeout=httpx.Timeout(30.0, connect=10.0)
    )

    try:
        response = await client.chat.completions.create(
            model="Qwen3-Coder",
            messages=[
                {"role": "user", "content": "你好"}
            ],
            stream=True,
            max_tokens=100
        )

        print("开始迭代响应...")
        async for chunk in response:
            print(f"Chunk type: {type(chunk)}")
            print(f"Chunk: {chunk}")
            if hasattr(chunk, 'choices') and chunk.choices:
                print(f"Choice delta: {chunk.choices[0].delta}")
            break  # 只打印第一个 chunk

        print("测试 4 通过!")
    except Exception as e:
        print(f"\n测试 4 失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


async def test_api_with_custom_headers():
    """测试带自定义头的 API 调用"""
    print("\n" + "=" * 50)
    print("测试 5: 带自定义头的 API 调用")
    print("=" * 50)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        base_url=url,
        api_key="sk-JVo8j1Qjpr4LdQ0bA1C7C5AcA129425fA297F67cC29b730c",
    )

    try:
        response = await client.chat.completions.create(
            model="Qwen3-Coder",
            messages=[
                {"role": "user", "content": "你好"}
            ],
            stream=True,
            max_tokens=100
        )

        print("响应对象:", response)
        print("响应 model:", response.model)
        print("响应 id:", response.id)

        count = 0
        async for chunk in response:
            count += 1
            print(f"Chunk {count}: {chunk}")
            if count >= 3:
                break

        print(f"共收到 {count} 个 chunks")
        print("测试 5 通过!")
    except Exception as e:
        print(f"\n测试 5 失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


async def main():
    """运行所有测试"""
    print("开始 LLM 调试测试...")
    print(f"Python 版本: {sys.version}")
    print(f"工作目录: {os.getcwd()}")

    await test_llm_basic()
    await test_llm_with_system_message()
    await test_llm_non_streaming()
    await test_direct_api_call()
    await test_api_with_custom_headers()

    print("\n" + "=" * 50)
    print("所有测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())