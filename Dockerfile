FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
# install Python dependencies
COPY requirements.txt requirements.lock.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt -r requirements.lock.txt

# copy app code + launcher
COPY app/ /app/app/
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8000

# IMPORTANT: shell doesn't expand in JSON form; run start.sh explicitly
CMD ["/app/start.sh"]
ARG CACHE_BUST=1757537621
