# syntax=docker/dockerfile:1

# Build both Vue applications with one Node toolchain.
FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /src/zdblog-vue-c
COPY zdblog-vue-c/package.json zdblog-vue-c/package-lock.json ./
RUN npm ci
COPY zdblog-vue-c/ ./
RUN npm run build

WORKDIR /src/zdblog-vue-s
COPY zdblog-vue-s/package.json zdblog-vue-s/package-lock.json ./
RUN npm ci
COPY zdblog-vue-s/ ./
RUN npm run build

# Nginx serves the C site and the S/admin site from one origin and proxies API calls.
FROM nginx:1.28-alpine AS web
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-builder /src/zdblog-vue-c/dist/ /usr/share/nginx/html/
COPY --from=frontend-builder /src/zdblog-vue-s/dist/ /usr/share/nginx/html/ZDAdmin/

# Django API and local BGE embedding runtime.
FROM python:3.12-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

WORKDIR /app
COPY zdblog-master/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch==2.11.0 \
    && pip install sentence-transformers==5.4.1

COPY zdblog-master/ /app/zdblog-master/
COPY models/bge-small-zh-v1.5/ /app/models/bge-small-zh-v1.5/
COPY models/ip2region/ /app/models/ip2region/
COPY docker/backend-entrypoint.sh /usr/local/bin/zdblog-entrypoint
RUN chmod 755 /usr/local/bin/zdblog-entrypoint \
    && useradd --system --create-home --uid 10001 app \
    && mkdir -p /app/zdblog-master/staticfiles \
    && chown -R app:app /app/zdblog-master/staticfiles

WORKDIR /app/zdblog-master
USER app
ENTRYPOINT ["/usr/local/bin/zdblog-entrypoint"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--access-logfile", "-"]
