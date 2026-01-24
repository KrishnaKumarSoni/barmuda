#!/bin/bash
# start.sh

# FORCE UNLIMITED MEMORY
# We rely on the Docker container limit (2GB) to stop us if we leak.
echo "Starting Redis with UNLIMITED memory..."
redis-server /app/redis.conf \
  --maxmemory 0 \
  --daemonize yes

echo "Waiting for Redis to boot..."
until redis-cli ping | grep -q PONG; do
  sleep 1
done
echo "Redis is up."

echo "Running Redis Init..."
python -m scripts.redis_init

echo "Starting Uvicorn..."
exec uvicorn service:app --host 0.0.0.0 --port $PORT