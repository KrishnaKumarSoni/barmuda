import asyncio
import time
import os
import sys
from dotenv import load_dotenv
import redis.asyncio as redis

# Add agent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_dir = os.path.dirname(current_dir)
sys.path.append(agent_dir)

load_dotenv(os.path.join(agent_dir, ".env"))

async def test_latency():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("Error: REDIS_URL not set in .env")
        return

    print(f"Connecting to Redis at {redis_url.split('@')[-1]}...") # Obfuscate password
    
    try:
        r = redis.from_url(redis_url)
        
        # Test 1: PING
        start = time.time()
        await r.ping()
        ping_time = time.time() - start
        print(f"PING Latency: {ping_time:.4f}s")
        
        # Test 2: SET/GET
        start = time.time()
        await r.set("latency_test", "foo")
        set_time = time.time() - start
        print(f"SET Latency: {set_time:.4f}s")
        
        start = time.time()
        val = await r.get("latency_test")
        get_time = time.time() - start
        print(f"GET Latency: {get_time:.4f}s")
        
        await r.delete("latency_test")
        await r.aclose()
        
    except Exception as e:
        print(f"Redis Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_latency())
