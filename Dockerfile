FROM python:3.12-slim

WORKDIR /app

# Install git for any VCS deps (safe; small)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (ONLY from requirements.txt)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy source code
COPY . /app

# Copy the rest of the app
COPY . .

# Railway provides $PORT; bind to all interfaces
ENV PORT=8000
EXPOSE 8000

# Start FastAPI (adjust module path if your app entrypoint differs)


CMD ["/app/start.sh"]

# ---- start script for migrations + app ----
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
