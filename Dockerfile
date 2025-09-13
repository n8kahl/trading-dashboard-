FROM python:3.12-slim

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates build-essential \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# python deps (layered for cache)
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements.lock.txt || true

# copy source code and launcher
COPY . /app
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# bake commit SHA for debugging
ARG COMMIT_SHA=unknown
ENV COMMIT_SHA=$COMMIT_SHA

# Railway sets PORT; default to 8080 for local
ENV PORT=8080

# run
CMD ["/app/start.sh"]
