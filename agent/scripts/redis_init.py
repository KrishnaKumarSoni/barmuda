# scripts/redis_init.py
# python -m scripts.redis_init

from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from core.redis_client import redis_client

import asyncio

async def init_redis():
    checkpointer = AsyncRedisSaver(redis_client=redis_client)
    # Creates necessary structures in Redis
    print("starting function")
    await checkpointer.asetup() 
    print("Redis checkpointer initialized.")
    

if __name__ == "__main__":
    asyncio.run(init_redis())