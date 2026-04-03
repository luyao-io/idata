import os
from redis import asyncio as aioredis
from dotenv import load_dotenv
from config import load_config
config = load_config()

# 创建全局的 Redis 客户端实例
redis_client = aioredis.Redis(
    host=config.redis.host,
    port=config.redis.port,
    password=config.redis.password,
    decode_responses=True,
    db=config.redis.db
)