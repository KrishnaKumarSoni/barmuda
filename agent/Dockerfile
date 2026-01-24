FROM python:3.11-slim

WORKDIR /app

# 1. Install Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy Application Code
COPY . .

# 3. Expose Port
ENV PORT 8080
EXPOSE 8080

# 4. Start the Agent API directly
CMD uvicorn service:app --host 0.0.0.0 --port $PORT
