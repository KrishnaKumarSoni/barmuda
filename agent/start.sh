#!/bin/bash

# 1. Start Redis in the background using your config
# We explicitly point to the config to ensure maxmemory settings are applied
echo "Starting Redis..."
redis-server /app/redis.conf --daemonize yes

# 2. Wait for Redis to be ready (loops until ping succeeds)
echo "Waiting for Redis to boot..."
until redis-cli ping | grep -q PONG; do
  sleep 1
done
echo "Redis is up."

# 3. Initialize your database (Run your init script)
echo "Running Redis Init..."
python -m scripts.redis_init

# 4. Start the backend
# exec replaces the shell process, so signals (like stopping the container) go to Uvicorn
echo "Starting Uvicorn..."
exec uvicorn service:app --host 0.0.0.0 --port $PORT