# Hardened image for the session 17 DevSecOps demo.
# - alpine base: trivy found 44 unfixed HIGH OS CVEs in python:3.12-slim (debian) vs 0 HIGH here,
#   and the image is half the size (24 MB vs 46 MB)
# - OS packages upgraded at build time, deps in a separate layer, no pip cache
# - runs as a non-root user (uid 10001), production WSGI server instead of the Flask dev server
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apk upgrade --no-cache

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

RUN adduser -D -u 10001 appuser
USER 10001

EXPOSE 5001
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/health')"
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--access-logfile", "-", "app.app:app"]
