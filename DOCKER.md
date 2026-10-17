# zdblog Docker 部署

仓库提供一个 Docker Compose 部署：PostgreSQL（含 pgvector）、Redis、Django API、Nginx 前端和 Caddy HTTPS 入口。Caddy 会为配置的域名自动申请并续期 TLS 证书，HTTP 请求会跳转到 HTTPS。RAG 使用阿里云百炼在线嵌入接口；后端镜像只包含 `models/ip2region` 离线地域数据库。服务器不需要另装 Python、Node.js 或 Conda。

## 服务器要求

- 安装 Docker Engine 和 Docker Compose v2 插件。
- 准备已解析到服务器公网 IP 的域名；服务器安全组和防火墙需允许公网 TCP 80、443 入站，以便网站访问和证书签发/续期。
- 建议至少 4 GB 内存。
- 服务器需能访问镜像仓库、Docker 构建阶段使用的 npm/Python 包源，以及阿里云百炼嵌入 API。
- 对外开放 Caddy 的 80 和 443 端口。PostgreSQL、Redis、Django 和 Nginx 只在 Docker 网络内部访问。

## 首次部署

将当前工程上传到服务器的 `/var/www/zdblog`，不要遗漏 `Dockerfile`、`docker-compose.yml`、`.env.docker.example`、`docker/`、两个前端目录、后端目录，以及 `models/ip2region`。不需要上传 `models/bge-small-zh-v1.5`、`node_modules`、开发机的 `.env` 或 Conda 环境。使用 Git 拉取时，先确认这些文件已提交并推送；本地未提交文件不会被带到服务器。

Docker Engine 和 Compose 插件的安装步骤见 [Docker 官方安装文档](https://docs.docker.com/engine/install/)。安装完成后，进入上传的工程根目录：

```sh
sudo mkdir -p /var/www/zdblog
sudo chown "$USER" /var/www/zdblog
cd /var/www/zdblog
docker --version
docker compose version
cp .env.docker.example .env.docker
chmod 600 .env.docker
```

编辑 `.env.docker`：填写足够长且随机的 `SECRET_KEY`、数据库与 Redis 密码、DeepSeek API Key、阿里云百炼 API Key 和 Workspace ID，并设置 `ACME_EMAIL` 作为证书服务联系邮箱。将 `ALLOWED_HOSTS` 设为浏览器访问所用的域名（例如 `zendee.top,www.zendee.top`）。RAG 的默认模型为 `qwen3.7-text-embedding-flash`，向量维度为 1024。不要把 `.env.docker` 提交到 Git。Caddy 根据 `docker/Caddyfile` 中的域名自动申请并续期证书；域名的 DNS A/AAAA 记录必须指向此服务器，且 80、443 端口可从公网访问。

编辑文件可使用 `nano .env.docker`。`ALLOWED_HOSTS` 填域名或 IP，不要加 `http://`、路径或端口。可以用 `openssl rand -hex 32` 生成随机密钥。Caddy 需要占用服务器的 80 和 443 端口；若已有其他服务占用这些端口，需要先调整端口占用或让现有反向代理接入 Caddy。

校验配置并启动：

```sh
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker ps
docker compose --env-file .env.docker logs -f backend
```

访问 `https://你的域名/` 使用 C 端，访问 `https://你的域名/ZDAdmin/` 使用 S 端。首次启动时 Caddy 会自动申请证书；稍等证书签发完成后即可通过 HTTPS 访问。后端启动时会先检查 PostgreSQL 中是否存在 `DB_NAME` 指定的库，不存在就创建；随后执行项目现有 Django 数据库迁移和 `collectstatic`。这只初始化新库的表结构，不会把旧 `zblog` 库中的数据复制到 `zdblog`。旧库和数据保持原样。数据库迁移完成后，若已有公开文章，运行一次 `rag_reindex --prune` 创建 1024 维嵌入索引。

如果使用全新数据库，确认后端完成迁移后创建管理员，再用该账号登录 S 端：

```sh
docker compose --env-file .env.docker exec backend python manage.py createsuperuser
```

云服务器安全组和系统防火墙需放行 TCP 80、443；当前配置不会向公网映射 PostgreSQL、Redis、Django 或 Nginx 的端口。

默认创建空的 `zdblog` 数据库。如果要迁移本机现有 PostgreSQL 数据，应先在服务器只启动 `db`，把 PostgreSQL dump 恢复到 `zdblog`，再启动 `backend` 和 `web`。MySQL 数据不能直接恢复到此 PostgreSQL 容器，需要先单独完成数据库迁移。

文章、用户、聊天、人物配置、系统配置和访问测试记录都位于数据库中，复制代码或构建镜像不会复制这些数据。迁移现有数据库时继续使用原有管理员账号，无需重新创建。

## 更新版本

先备份数据库，在 `/var/www/zdblog` 更新仓库代码后执行：

```sh
cd /var/www/zdblog
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker logs -f backend
```

后端启动时会自动应用迁移。发布包含 RAG 模型或索引结构更新后，运行以下命令重建公开文章索引：

```sh
docker compose --env-file .env.docker exec backend python manage.py rag_reindex --prune
```

## 备份与恢复

备份 PostgreSQL：

```sh
sudo install -d -m 700 -o "$USER" -g "$(id -gn)" /var/backups/zdblog
docker compose --env-file .env.docker exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > "/var/backups/zdblog/zdblog-$(date +%F-%H%M%S).sql"
```

恢复到已创建的数据库：

```sh
# 将文件名替换为上一步生成的时间戳备份文件
docker compose --env-file .env.docker exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"' < /var/backups/zdblog/zdblog-YYYY-MM-DD-HHMMSS.sql
```

`postgres_data` 包含博客、聊天记录、人物和 RAG 向量；`redis_data` 保存 Redis AOF；`static_data` 保存 Django 静态资源；`caddy_data` 保存证书和 ACME 状态。移除容器时不要加 `-v`，否则会删除这些命名卷。定期将数据库备份复制到服务器以外的位置。

## 常用运维命令

```sh
docker compose --env-file .env.docker logs -f
docker compose --env-file .env.docker restart backend
docker compose --env-file .env.docker down
docker compose --env-file .env.docker exec backend python manage.py rag_status
```

Docker 部署通过 `.env.docker` 中的 `RAG_EMBED_BASE_URL`、`RAG_EMBED_API_KEY` 和 `RAG_EMBED_MODEL` 调用在线嵌入服务。服务器不需要复制开发机的 `.env` 或本地 BGE 模型。
