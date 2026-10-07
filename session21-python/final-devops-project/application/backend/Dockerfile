# REGISTRY lets local builds use a Docker Hub mirror (e.g. mirror.gcr.io/library) when rate-limited.
ARG REGISTRY=docker.io/library
FROM ${REGISTRY}/python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apk upgrade --no-cache && adduser -D -u 10001 app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

ARG APP_VERSION=1.0.0
ENV APP_VERSION=${APP_VERSION}

USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
# Migrations first, then the API (two workers; Kubernetes scales pods horizontally).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers"]
