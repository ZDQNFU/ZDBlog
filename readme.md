# ZDBlog

ZDBlog 是一个基于 Django REST Framework 和 Vue 3 的个人博客系统，包含博客前台、管理后台、AI 聊天、站内文章检索（RAG）和资源分享功能。

生产环境推荐使用 Docker Compose，部署、备份与更新步骤见 [Docker 部署指南](DOCKER.md)。本地 RAG 配置和索引维护见 [RAG 运行说明](zdblog-master/rag/readme.md)，聊天 Agent 说明见 [聊天机器人文档](zdblog-master/chat_robot/readme.md)。

## 功能

- **博客前台**：文章列表、分类与标签筛选、搜索、Markdown 阅读、目录导航、评论与点赞；支持私密文章密码验证。
- **管理后台**：文章编辑与图片上传、标签和分类、评论、用户、留言、资源链接、聊天人物与记录、访客统计和系统配置管理。
- **AI 聊天**：LangGraph Agent、流式响应、DeepSeek 兼容接口；可配置站内 RAG、联网搜索、天气及角色工具。
- **站内 RAG**：使用 PostgreSQL/pgvector 保存公开文章索引，默认通过阿里云百炼 Qwen 在线生成 1024 维向量，并结合词法检索。
- **其他**：JWT 认证、邮箱验证码、访客追踪、Redis 缓存、暗色主题。

## 技术栈

| 层 | 主要技术 |
| --- | --- |
| 后端 | Python 3.12、Django 6、Django REST Framework、Simple JWT、Gunicorn |
| 数据库与缓存 | PostgreSQL 17、pgvector、pg_trgm、Redis 7 |
| AI | LangChain、LangGraph、DeepSeek API、阿里云百炼 Qwen 在线嵌入模型 |
| 前端 | Vue 3、Vue Router、Pinia、Element Plus、Vite 8 |
| 管理端可视化 | Chart.js、ECharts |
| 部署 | Docker Compose、Caddy（自动 HTTPS）、Nginx |

## 项目结构

```text
zdblog/
├── zdblog-master/       # Django API、聊天 Agent 和 RAG
├── zdblog-vue-c/        # 博客前台
├── zdblog-vue-s/        # 管理后台（部署路径 /ZDAdmin/）
├── models/              # ip2region 离线地域数据库
├── docker/              # Nginx、容器启动配置
├── docs/                # RAG 评测数据和设计资料
├── Dockerfile
├── docker-compose.yml
└── DOCKER.md             # 生产部署指南
```

## Docker 快速部署

需要安装 Docker Engine 与 Docker Compose v2。复制示例环境文件并填写密钥、数据库密码、允许访问的域名和 DeepSeek API Key：

```sh
cp .env.docker.example .env.docker
# 编辑 .env.docker
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker exec backend python manage.py createsuperuser
```

部署会通过 Caddy 自动申请和续期 HTTPS 证书；需先将域名解析到服务器，并开放 TCP 80、443。博客使用 HTTPS 域名访问，管理后台位于 `/ZDAdmin/`。详细服务器要求、配置说明、更新和数据库备份步骤请按 [DOCKER.md](DOCKER.md) 操作。`.env.docker` 含敏感配置，不要提交到 Git。

## 本地开发

### 环境要求

- Python 3.12+
- Node.js 20.19+ 或 22.12+
- PostgreSQL 17，启用 `pgvector` 和 `pg_trgm` 扩展
- Redis 7

本地配置放在 `zdblog-master/.env`，至少设置 Django `SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS`、PostgreSQL `DB_ENGINE`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`，以及 Redis 连接信息。聊天功能还需设置 `DEEPSEEK_API_KEY`；邮箱验证码需配置 SMTP。RAG 的本地模型路径和嵌入环境配置见 [RAG 运行说明](zdblog-master/rag/readme.md)。

```sh
# 后端
cd zdblog-master
python -m venv .venv
# 激活虚拟环境后安装依赖
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8000
```

另开终端启动前端。Vite 开发服务器会将 `/api` 请求代理到 `http://localhost:8000`；C 端默认端口 5173，S 端默认端口 5174。

```sh
# 博客前台
cd zdblog-vue-c
npm ci
npm run dev

# 管理后台（另开终端）
cd zdblog-vue-s
npm ci
npm run dev
```

创建全新本地数据库后，可在后端目录运行 `python manage.py createsuperuser` 创建管理账号。需要重建公开文章向量索引时运行 `python manage.py rag_reindex --prune`；查看索引状态运行 `python manage.py rag_status`。

## API 与页面

- 前台页面：`/`、`/articles`、`/article/:id`、`/chat`、`/resources`、`/message-board`
- 管理后台：`/ZDAdmin/`（开发服务器为 `http://localhost:5174/ZDAdmin/`）
- API 根路径：`/api/`，按文章、用户认证、聊天、链接、留言、访客追踪和系统配置等资源划分。

## 许可证

MIT
