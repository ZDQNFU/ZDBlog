# ZDBlog — 个人博客系统

基于 Django + Vue3 构建的个人博客系统，包含博客前台、管理后台、AI 聊天机器人和资源分享功能。

## 技术栈

### 后端
- **Django 6.0** + **Django REST Framework 3.16** — RESTful API
- **Simple JWT 5.5** — 基于 JWT 的用户认证（access 2h / refresh 7d）
- **MySQL 8.0** — 主数据库（mysqlclient 2.2）
- **LangChain 1.3** + **LangGraph** — AI Agent 框架
- **LangGraph Checkpoint SQLite** — Agent 对话状态持久化
- **DeepSeek API** — LLM 模型调用（通过 langchain-openai）
- **Redis 7** — 缓存后端（django-redis 5.4 + redis-py 5.2）
- **django-tracking2** — 访客行为追踪

### 前端
- **Vue 3.5** (Composition API + `<script setup>`)
- **Vue Router 5** — 路由管理
- **Pinia 3** — 状态管理
- **Element Plus 2.14** — UI 组件库
- **marked** + **highlight.js** — Markdown 渲染与代码高亮
- **md-editor-v3** — S 端 Markdown 编辑器
- **Chart.js** + **ECharts 6** — 数据图表与地图可视化
- **Axios** — S 端 HTTP 客户端
- **Vite 8** — 构建工具

## 项目结构

```
zdblog/
├── zdblog-master/                  # Django 后端
│   ├── config/                     # 项目配置（settings、URL 路由）
│   ├── article/                    # 文章应用
│   │   ├── models.py               # Article、Category、Tag、Comment、Like
│   │   ├── serializers/            # 序列化器（列表/详情/评论）
│   │   ├── views/                  # C端视图（c_views）+ S端视图（s_views）
│   │   ├── services/               # 业务逻辑层
│   │   └── urls.py                 # 路由（/api/articles/c/、/api/articles/s/）
│   ├── user/                       # 用户应用
│   │   ├── views.py                # 注册、登录、JWT、用户管理
│   │   ├── chat_views.py           # 聊天视图（同 chat_robot 的副本实现）
│   │   ├── serializers.py          # 用户序列化器
│   │   ├── captcha.py              # 算式图形验证码
│   │   ├── email_verification.py   # 邮箱验证码（QQ SMTP）
│   │   ├── permissions.py          # IsSuperAdmin 权限类
│   │   └── throttling.py           # 登录限流（指数退避）
│   ├── chat_robot/                 # 聊天机器人应用
│   │   ├── agent.py                # LangGraph Agent 初始化（DeepSeek + 工具 + 摘要中间件）
│   │   ├── models.py               # ChatMessage 模型（MySQL 持久化）
│   │   ├── views.py                # SSE 流式响应、聊天记录管理
│   │   ├── tools.py                # Agent 工具（天气、搜索、情感分析）
│   │   ├── prompts.py              # System Prompt（明日香角色扮演）
│   │   ├── utils.py                # LLM 工厂、流式响应、DeepSeek reasoning_content 适配
│   │   ├── urls.py                 # 路由（/api/chat-robot/）
│   │   └── data/asuka_memory.db    # LangGraph SQLite checkpoint 数据库
│   ├── link/                       # 资源链接应用
│   │   ├── models.py               # ResourceLink 模型
│   │   └── views/                  # C端列表 + S端CRUD
│   ├── message/                    # 留言板应用
│   │   ├── models.py               # Message、MessageLike 模型
│   │   └── views/                  # C端列表/创建/点赞 + S端管理
│   ├── system_config/              # 系统配置应用（KV 键值存储）
│   │   ├── models.py               # SystemConfig 模型（支持加密字段）
│   │   └── views.py                # S端 CRUD
│   ├── tracking_api/               # 访客追踪 API
│   │   ├── serializers.py          # Visitor、Pageview 序列化器
│   │   └── views.py                # 访客列表/详情/删除/地理位置
│   └── tools/                      # 工具模块
│       ├── generate_nums.py        # UUID v7 生成、Django signing 加密/解密
│       ├── image_controller.py     # 图片压缩、上传到 GitHub CDN
│       └── cache_utils.py          # Redis 缓存装饰器与失效辅助函数
│
├── zdblog-vue-c/                   # Vue3 C端（博客前台）
│   └── src/
│       ├── views/                  # 页面组件（6 个）
│       │   ├── HomeView.vue           # 首页（文章列表 + 侧栏）
│       │   ├── ArticleListView.vue    # 文章列表（标签/分类筛选 + 搜索）
│       │   ├── ArticleDetailView.vue  # 文章详情（Markdown 渲染 + 目录 + 评论）
│       │   ├── ChatView.vue           # AI 聊天（SSE 流式响应，需 staff 权限）
│       │   ├── ResourceView.vue       # 资源分享（卡片网格）
│       │   └── MessageBoardView.vue   # 留言板
│       ├── components/             # 公共组件（11 个）
│       │   ├── ArticleCard.vue     # 文章卡片
│       │   ├── ArticleTOC.vue      # 文章目录导航
│       │   ├── AuthModal.vue       # 登录/注册弹窗
│       │   ├── CommentForm.vue     # 评论表单
│       │   ├── EmojiPicker.vue     # Emoji 表情选择器
│       │   ├── MessageCard.vue     # 留言卡片
│       │   ├── Pagination.vue      # 分页组件
│       │   ├── SearchBox.vue       # 搜索框
│       │   ├── SidePanel.vue       # 侧栏面板
│       │   ├── SiteFooter.vue      # 页脚
│       │   └── UserAvatar.vue      # 用户头像
│       ├── stores/auth.js          # 认证状态（Pinia）
│       ├── composables/useTheme.js # 暗黑模式切换
│       ├── router/index.js         # 路由配置（含鉴权守卫）
│       └── api/index.js            # API 请求封装（原生 fetch + SSE）
│
└── zdblog-vue-s/                   # Vue3 S端（管理后台）
    └── src/
        ├── views/                  # 管理页面（13 个）
        │   ├── DashboardView.vue       # 数据仪表盘（Chart.js 图表）
        │   ├── ArticleManageView.vue   # 文章管理
        │   ├── ArticleEditView.vue     # 文章编辑（md-editor-v3）
        │   ├── TagManageView.vue       # 标签管理
        │   ├── CategoryManageView.vue  # 分类管理
        │   ├── CommentManageView.vue   # 评论管理
        │   ├── UserManageView.vue      # 用户管理（仅 superuser）
        │   ├── ResourceManageView.vue  # 资源链接管理
        │   ├── ChatManageView.vue      # 聊天记录管理
        │   ├── TrackingManageView.vue  # 访客追踪（ECharts 地图）
        │   ├── MessageManageView.vue   # 留言管理
        │   ├── SystemConfigView.vue    # 系统配置管理（仅 superuser）
        │   └── LoginView.vue           # 登录页
        ├── api/                    # API 模块（12 个，按资源拆分）
        │   ├── index.js            # Axios 实例（JWT 自动刷新 + 请求队列）
        │   ├── auth.js             # 登录/登出/用户信息/统计
        │   ├── articles.js         # 文章 CRUD
        │   ├── categories.js       # 分类 CRUD
        │   ├── tags.js             # 标签 CRUD
        │   ├── comments.js         # 评论管理
        │   ├── users.js            # 用户管理
        │   ├── links.js            # 资源链接 CRUD
        │   ├── chats.js            # 聊天记录管理
        │   ├── tracking.js         # 访客追踪
        │   ├── messages.js         # 留言管理
        │   └── systemConfig.js     # 系统配置 CRUD
        ├── components/AdminLayout.vue  # 管理端侧栏布局
        ├── stores/auth.js          # 认证状态
        ├── composables/useTheme.js # 暗黑模式切换
        ├── assets/china.json       # 中国地图 GeoJSON（ECharts 访客地图）
        └── router/index.js         # 路由配置（含鉴权守卫）
```

## 功能特性

### 博客前台（C 端）
- 文章列表（分页、标签、分类筛选、搜索）
- 文章详情（Markdown 渲染 + 代码高亮 + 目录导航）
- 公开文章与私密文章（需密码验证，密码为作者密码）
- 评论系统（支持回复与嵌套，需登录）
- 点赞/取消点赞（幂等操作）
- AI 聊天机器人（SSE 流式响应，需 staff 权限）
- 资源链接分享（响应式卡片网格）
- 留言板（支持匿名留言、emoji、点赞）
- 暗黑模式（localStorage 持久化）

### 管理后台（S 端）
- 数据仪表盘（Chart.js 趋势图 + 饼图）
- 文章 CRUD（Markdown 编辑器 + 实时预览，图片上传至 GitHub CDN）
- 标签、分类管理
- 评论管理
- 用户管理（仅超级管理员）
- 聊天记录管理（按用户查看、清空、裁剪）
- 访客追踪（ECharts 中国地图 + 访问明细 + IP 反查）
- 留言管理（列表、隐藏、删除）
- 资源链接管理
- 系统配置管理（KV 键值存储，支持加密字段，仅超级管理员）
- 暗黑模式

### 聊天机器人
- 基于 LangGraph 的 Agent 架构
- 明日香角色扮演（定制 System Prompt）
- 工具调用：天气查询（open-meteo）、网络搜索（博查）、中文情感分析
- DeepSeek reasoning_content 适配（模型思考过程注入回复）
- SummarizationMiddleware — 对话超过 10000 token 自动摘要，保留最近 50 条消息
- MySQL + SQLite 双写持久化（MySQL 存消息记录，SQLite 存 LangGraph checkpoint）
- SSE 流式响应
- 管理端可按用户查看、清空、裁剪聊天记录

## 数据库设计

所有自定义表主键使用 UUID v7（32 位十六进制字符串，时间可排序）。

### 核心表

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| `article` | 文章 | title, slug, summary, content_md, content_html, cover, status, view_count, like_count, comment_count, author, category, tags, published_at |
| `article_category` | 文章分类 | name |
| `article_tag` | 文章标签 | name, color |
| `article_comment` | 文章评论 | article, author (User FK), parent (自引用), content |
| `article_like` | 文章点赞 | article, user (唯一约束) |
| `chat_messages` | 聊天记录 | user, role (user/ai), content, token_count |
| `link_link` | 资源链接 | name, url, image_url, color, description |
| `message` | 留言板 | user (可空), content, like_count, is_hidden |
| `message_like` | 留言点赞 | message, user (唯一约束) |
| `system_config` | 系统配置 | key (唯一), value, value_type, description, is_encrypted |
| `auth_user` | 用户 | Django 内置 User 模型 |

### 文章状态
- `draft` — 草稿（仅 S 端可见）
- `published` — 已发布（C 端可见）
- `private` — 私密（C 端列表可见，详情需验证作者密码）

## Redis 缓存

项目使用 Redis 作为缓存后端，对高频读取的接口做短时效缓存，数据库变更时自动失效。

### 缓存配置

缓存后端通过 django-redis 接入，配置位于 `config/settings.py` 的 `CACHES` 字典：

- **后端**：`django_redis.cache.RedisCache`
- **序列化**：Pickle（配合 `ZlibCompressor` 压缩）
- **Key 前缀**：`zblog`（自动添加，避免多项目共用同一 Redis 实例时的键冲突）
- **连接超时**：5s（`SOCKET_CONNECT_TIMEOUT`）、`SOCKET_TIMEOUT`）

### 缓存策略

| 缓存键 | 过期时间 | 覆盖接口 | 失效触发 |
|--------|----------|----------|----------|
| `dashboard:stats` | 300s (5min) | S 端仪表盘统计 | 文章/标签/分类/评论的增删改 |
| `c:messages` | 30s | C 端留言列表 | 留言创建（C + S 端）、留言更新/删除（S 端） |
| `c:tags` | 3600s (1h) | C 端标签列表 | 标签增删改 |
| `c:links` | 1800s (30min) | C 端资源链接列表 | 链接增删改 |
| `c:random_articles` | 300s (5min) | C 端随机推荐文章 | 文章增删改 |

### 缓存失效机制

所有数据变更操作（Create / Update / Delete）在 `perform_create`、`perform_update`、`perform_destroy` 中调用 `invalidate(*keys)` 清理对应缓存。下个请求到达时自动回源数据库并重新缓存。

```python
from tools.cache_utils import cache_result, invalidate

# 读接口：装饰器自动处理缓存命中/回源
@cache_result('dashboard:stats', timeout=300)
def get(self, request):
    ...

# 写接口：数据变更后清理缓存
def perform_create(self, serializer):
    serializer.save(author=self.request.user)
    invalidate('dashboard:stats', 'c:random_articles')
```

### 工具函数

`tools/cache_utils.py` 提供四个辅助函数：

| 函数 | 用途 |
|------|------|
| `cache_result(key, timeout)` | 装饰器，缓存 DRF APIView 方法的响应数据 |
| `cached_or_fetch(key, timeout, fetch_func)` | 命令式缓存读取，未命中则调用 fetch_func |
| `invalidate(*keys)` | 批量删除指定缓存键 |
| `invalidate_pattern(pattern)` | 按通配符模式删除缓存（依赖 django-redis 扩展） |

### IP 地理位置缓存

`tracking_api/views.py` 的 `VisitorGeoView` 直接使用 Django cache 对单个 IP 的地理位置查询结果做缓存（key: `ip_geo_v2_{ip}`，有效期 86400s），避免重复请求外部 API。

## 快速开始

### 环境要求
- Python 3.12+
- Node.js 22.12+
- MySQL 8.0+
- Redis 7+

### 后端配置

```bash
cd zdblog-master

# 创建虚拟环境
conda create -n zblog python=3.12

# 安装依赖
pip install -r requirements.txt

# 确保 Redis 服务已启动（默认 localhost:6379）

# 创建 config/settings.py（参考下方环境变量说明）

# 数据库迁移
python manage.py migrate

# 启动开发服务器
python manage.py runserver 8000
```

### 前端配置

```bash
# C 端（博客前台）
cd zdblog-vue-c
npm install
npm run dev        # 开发模式
npm run build      # 生产构建

# S 端（管理后台）
cd zdblog-vue-s
npm install
npm run dev        # 开发模式
npm run build      # 生产构建
```

### 环境变量

需在 `zdblog-master/.env` 中配置以下关键项：

- `SECRET_KEY` — Django 密钥
- `DB_*` — MySQL 数据库连接信息（ENGINE / NAME / USER / PASSWORD / HOST / PORT）
- `REDIS_HOST` / `REDIS_PORT` / `REDIS_PASSWORD` / `REDIS_DB` — Redis 连接信息
- `DEEPSEEK_API_KEY` — DeepSeek API 密钥
- `DEEPSEEK_BASE_URL` — DeepSeek API 地址
- `SEARCH_URL` / `SEARCH_API_KEY` — 博查网络搜索 API
- `EMAIL_*` — QQ 邮箱 SMTP 配置（验证码发送）
- `ZDBLOG_C` / `ZDBLOG_S` — C 端 / S 端前端地址（CORS 白名单）

## API 概览

### 公开 / C 端接口

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/api/articles/c/list/` | 文章列表（分页、搜索） | 否 |
| GET | `/api/articles/c/<id>/` | 文章详情 | 否 |
| POST | `/api/articles/c/<id>/verify/` | 私密文章密码验证 | 否 |
| GET | `/api/articles/c/tags/` | 标签列表 | 否 |
| GET | `/api/articles/c/random/` | 随机文章 | 否 |
| POST | `/api/articles/c/comments/` | 创建评论 | 是 |
| POST | `/api/articles/c/<id>/like/` | 点赞文章 | 是 |
| DELETE | `/api/articles/c/<id>/like/` | 取消点赞 | 是 |
| POST | `/api/auth/register/` | 用户注册 | 否 |
| POST | `/api/auth/login/` | 用户登录 | 否 |
| GET | `/api/auth/me/` | 当前用户信息 | 是 |
| POST | `/api/auth/send-code/` | 发送邮箱验证码 | 否 |
| GET | `/api/auth/captcha/` | 获取算式验证码 | 否 |
| POST | `/api/chat-robot/stream/` | 聊天 SSE 流式响应 | 是（staff） |
| GET | `/api/chat-robot/history/` | 聊天历史（近 30 天） | 是 |
| GET | `/api/links/c/links/` | 资源链接列表 | 否 |
| GET | `/api/messages/c/list/` | 留言列表 | 否 |
| POST | `/api/messages/c/create/` | 创建留言 | 否（自动绑定已登录用户） |
| POST/DELETE | `/api/messages/c/<id>/like/` | 点赞/取消留言 | 是 |

### 管理 / S 端接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/articles/s/articles/` | 文章列表 / 创建 |
| GET/PATCH/DELETE | `/api/articles/s/articles/<id>/` | 文章详情 / 更新 / 删除 |
| POST | `/api/articles/s/upload-image/` | 上传图片到 GitHub CDN |
| GET/POST | `/api/articles/s/tags/` | 标签列表 / 创建 |
| GET/PATCH/DELETE | `/api/articles/s/tags/<id>/` | 标签详情 / 更新 / 删除 |
| GET/POST | `/api/articles/s/categories/` | 分类列表 / 创建 |
| GET/PATCH/DELETE | `/api/articles/s/categories/<id>/` | 分类详情 / 更新 / 删除 |
| GET | `/api/articles/s/comments/` | 评论列表 |
| DELETE | `/api/articles/s/comments/<id>/` | 删除评论 |
| GET/POST | `/api/auth/users/` | 用户列表 / 创建（仅 superuser） |
| GET/PATCH/DELETE | `/api/auth/users/<pk>/` | 用户详情 / 更新 / 删除 |
| GET | `/api/chat-robot/users/` | 聊天用户列表 |
| GET | `/api/chat-robot/users/<id>/` | 用户聊天详情 |
| POST | `/api/chat-robot/users/<id>/clear/` | 清空聊天记录（MySQL + SQLite） |
| POST | `/api/chat-robot/users/<id>/trim/` | 裁剪旧聊天记录 |
| GET/POST | `/api/links/s/links/` | 资源链接列表 / 创建 |
| GET/PATCH/DELETE | `/api/links/s/links/<id>/` | 资源链接详情 / 更新 / 删除 |
| GET/POST | `/api/messages/s/messages/` | 留言列表 / 创建 |
| GET/PATCH/DELETE | `/api/messages/s/messages/<id>/` | 留言详情 / 更新 / 删除 |
| GET/POST | `/api/system-config/s/configs/` | 系统配置列表 / 创建 |
| GET/PATCH/DELETE | `/api/system-config/s/configs/<id>/` | 配置详情 / 更新 / 删除 |
| GET | `/api/tracking/visitors/` | 访客列表（可搜索 IP/用户名） |
| GET | `/api/tracking/visitors/<session_key>/` | 访客详情 |
| DELETE | `/api/tracking/visitors/<session_key>/` | 删除访客记录 |
| POST | `/api/tracking/visitors/delete/` | 批量删除访客 |
| GET | `/api/tracking/visitors/geo/` | 访客 IP 地理位置反查 |

## License

MIT
