# REGISTRY lets local builds use a Docker Hub mirror (e.g. mirror.gcr.io) when rate-limited.
ARG REGISTRY=docker.io

# Stage 1: build the static bundle with Node
FROM ${REGISTRY}/library/node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve it with an unprivileged nginx (runs as uid 101, listens on 8080).
# 1.29-alpine (alpine 3.23) had 42 fixable HIGH CVEs (curl, c-ares, ...) -> newer base + apk upgrade.
FROM ${REGISTRY}/nginxinc/nginx-unprivileged:1.31-alpine
USER root
RUN apk upgrade --no-cache
ENV BACKEND_URL=http://backend:8000
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
EXPOSE 8080
USER 101
