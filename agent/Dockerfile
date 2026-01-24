# Use bookworm (stable)
FROM python:3.11-bookworm

# 1. Install prerequisites
RUN apt-get update && apt-get install -y curl wget libgomp1 redis-tools && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Redis Stack manually
RUN wget -qO- https://packages.redis.io/redis-stack/redis-stack-server-7.2.0-v9.jammy.x86_64.tar.gz | \
    tar xz -C /opt && \
    mv /opt/redis-stack-server-* /opt/redis-stack

# 3. Add Redis binaries to path
ENV PATH="/opt/redis-stack/bin:$PATH"

# 4. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Application Code & Configs
COPY . .

# 6. Make start script executable
RUN chmod +x start.sh

# 7. Environment Variables
ENV PORT=8080
ENV REDIS_HOST=localhost
ENV REDIS_PORT=6379

# 8. Start via the script
CMD ["./start.sh"]