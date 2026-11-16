# Smart Health Food AI - Docker image
# Build:  docker build -t smart-health-food-ai .
# Run:    docker run -p 5000:5000 smart-health-food-ai

# 1. Start from a small official Python image
FROM python:3.12-slim

# 2. Work inside /app
WORKDIR /app

# 3. Install dependencies first (Docker caches this step)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the application code
COPY . .

# 5. The app listens on port 5000
EXPOSE 5000

# 6. Start the server (1 worker: the memory fallback is per-process)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "app:app"]
