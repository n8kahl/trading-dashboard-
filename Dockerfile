FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# minimal deps to boot FastAPI
RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx

# copy app code + launcher
COPY app/ /app/app/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8000

# IMPORTANT: shell doesn't expand in JSON form; run start.sh explicitly
CMD ["/app/start.sh"]
ARG CACHE_BUST=1757537621
