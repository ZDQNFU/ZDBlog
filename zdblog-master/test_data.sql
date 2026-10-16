-- ============================================
-- ZBlog 测试数据
-- 使用前请确保：
-- 1. 已运行 python manage.py migrate
-- 2. 至少存在一个用户（auth_user 表中有 id=1 的记录）
--   如没有，先通过 python manage.py createsuperuser 创建
-- ============================================

USE zdblog;

INSERT INTO `auth_user` (
    `id`,
    `password`,
    `last_login`,
    `is_superuser`,
    `username`,
    `first_name`,
    `last_name`,
    `email`,
    `is_staff`,
    `is_active`,
    `date_joined`
) VALUES
(
    1,
    'pbkdf2_sha256$260000$6tHk5qZ9XvW8$TQ9uXl2K7mN4pR8vW1yF6bJ3cH5aE9dG2iL7oM0sU=',
    '2026-05-15 10:00:00.000000',
    1,  -- 超级用户
    'admin',
    '',
    '',
    'admin@example.com',
    1,  -- staff 权限
    1,  -- 激活状态
    '2026-05-01 10:00:00.000000'
),
(
    2,
    'pbkdf2_sha256$260000$8xM4nQ2kL9pW$A3rF7yH1jN6bV9cX2zE5gI8kM0oL4pR7tU3wQ6sZ=',
    '2026-05-14 09:00:00.000000',
    0,
    'zhangsan',
    '三',
    '张',
    'zhangsan@example.com',
    0,
    1,
    '2026-04-15 08:00:00.000000'
),
(
    3,
    'pbkdf2_sha256$260000$2dF7jK9lM3nQ$Y5tR8vW1xZ4aB7cE0gH2jL5pO8sU3yF6iK9mN2qT=',
    '2026-05-13 14:00:00.000000',
    0,
    'lisi',
    '四',
    '李',
    'lisi@example.com',
    0,
    1,
    '2026-04-20 10:30:00.000000'
),
(
    4,
    'pbkdf2_sha256$260000$5gH9jM2nQ7tW$C8uR3xY6zB1eF4aD7gJ0kL9oP2sV5yH8mN1qT4wX=',
    '2026-05-12 11:00:00.000000',
    0,
    'wangwu',
    '五',
    '王',
    'wangwu@example.com',
    0,
    1,
    '2026-05-01 09:15:00.000000'
),
(
    5,
    'pbkdf2_sha256$260000$7jL2nQ9tX4rZ$E0uW3yA6cF9iD2gM5pR8sV1bH4kL7oQ0tN3xU6zY=',
    NULL,
    0,
    'zhaoliu',
    '六',
    '赵',
    'zhaoliu@example.com',
    0,
    1,
    '2026-05-05 14:20:00.000000'
);


-- ============================================
-- 1. 分类（2 个）
-- ============================================
INSERT INTO `article_category` (`id`, `name`, `created_by_id`, `updated_by_id`, `created_at`, `updated_at`) VALUES
('11111111111141118111111111111111', '技术', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000'),
('22222222222242228222222222222222', '生活', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000');

-- ============================================
-- 2. 标签（8 个）
-- ============================================
INSERT INTO `article_tag` (`id`, `name`, `color`, `created_by_id`, `updated_by_id`, `created_at`, `updated_at`) VALUES
('aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa1', 'Python',   '#3b82f6', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000'),
('aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa2', 'Django',   '#10b981', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000'),
('aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa3', 'JavaScript','#f59e0b', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000'),
('aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa4', 'Vue',      '#8b5cf6', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000'),
('aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa5', '数据库',   '#ef4444', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000'),
('aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa6', '前端',     '#06b6d4', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000'),
('aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa7', '后端',     '#6366f1', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000'),
('aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa8', 'DevOps',   '#f97316', 1, 1, '2026-04-15 10:00:00.000000', '2026-04-15 10:00:00.000000');

-- ============================================
-- 3. 文章（10 篇）
-- ============================================
INSERT INTO `article` (`id`, `title`, `slug`, `summary`, `content_md`, `content_html`, `cover`, `status`, `view_count`, `like_count`, `comment_count`, `author_id`, `category_id`, `published_at`, `created_at`, `updated_at`) VALUES

-- 文章 1
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01',
 'Python 异步编程入门：从回调到 async/await',
 'python-async-intro',
 '本文带你从零理解 Python 异步编程，包括回调函数、Future、协程以及 async/await 语法的演进历程。',
 '# Python 异步编程入门\n\n## 为什么需要异步？\n\n在传统的同步编程中，当程序执行 I/O 操作（如网络请求、文件读写）时，必须**等待**该操作完成后才能继续执行后续代码。这在高并发场景下效率极低。\n\n```python\nimport time\n\ndef fetch(url):\n    time.sleep(2)  # 模拟网络延迟\n    return f"data from {url}"\n\ndef main():\n    urls = ["url1", "url2", "url3"]\n    results = [fetch(url) for url in urls]  # 耗时 6 秒\n```\n\n## async/await 登场\n\nPython 3.5 引入的 async/await 语法彻底改变了异步编程体验：\n\n```python\nimport asyncio\n\nasync def fetch(url):\n    await asyncio.sleep(2)\n    return f"data from {url}"\n\nasync def main():\n    urls = ["url1", "url2", "url3"]\n    tasks = [fetch(url) for url in urls]\n    results = await asyncio.gather(*tasks)  # 仅耗时 2 秒\n```\n\n## 总结\n\n异步编程不是银弹，但对于 I/O 密集型应用，它带来的性能提升是巨大的。',
 '<h1>Python 异步编程入门</h1><h2>为什么需要异步？</h2><p>在传统的同步编程中，当程序执行 I/O 操作时必须<strong>等待</strong>该操作完成后才能继续执行。</p><pre><code>import time\n\ndef fetch(url):\n    time.sleep(2)\n    return f"data from {url}"</code></pre><h2>async/await 登场</h2><p>Python 3.5 引入的 async/await 语法彻底改变了异步编程体验。</p><pre><code>import asyncio\n\nasync def fetch(url):\n    await asyncio.sleep(2)\n    return f"data from {url}"</code></pre>',
 'https://picsum.photos/seed/python-async/800/400',
 'published', 1283, 89, 7, 1, '11111111111141118111111111111111',
 '2026-05-01 09:00:00.000000', '2026-05-01 08:30:00.000000', '2026-05-03 14:00:00.000000'),

-- 文章 2
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02',
 'Django REST Framework 实战：构建高效 RESTful API',
 'django-drf-practical-guide',
 '深入探讨 DRF 的核心概念——序列化器、视图集、认证与权限，配合实战案例构建生产级 API。',
 '# Django REST Framework 实战\n\n## 环境准备\n\n```bash\npip install djangorestframework\n```\n\n在 `settings.py` 中添加：\n\n```python\nINSTALLED_APPS = [\n    ...\n    ''rest_framework'',\n]\n\nREST_FRAMEWORK = {\n    ''DEFAULT_PAGINATION_CLASS'': ''rest_framework.pagination.PageNumberPagination'',\n    ''PAGE_SIZE'': 10,\n}\n```\n\n## 序列化器\n\n序列化器是 DRF 的核心，负责将复杂的数据类型（如 Django 模型）转换为 JSON：\n\n```python\nfrom rest_framework import serializers\nfrom .models import Article\n\nclass ArticleSerializer(serializers.ModelSerializer):\n    class Meta:\n        model = Article\n        fields = ''__all__''\n```\n\n## ViewSet 路由\n\n使用 ModelViewSet 可以快速生成 CRUD 接口：\n\n```python\nfrom rest_framework.viewsets import ModelViewSet\n\nclass ArticleViewSet(ModelViewSet):\n    queryset = Article.objects.all()\n    serializer_class = ArticleSerializer\n```\n\n## 认证与权限\n\nDRF 提供了丰富的认证和权限机制，实际项目中建议结合 JWT 使用。',
 '<h1>Django REST Framework 实战</h1><h2>环境准备</h2><pre><code>pip install djangorestframework</code></pre><h2>序列化器</h2><p>序列化器是 DRF 的核心，负责将复杂的数据类型转换为 JSON。</p><h2>认证与权限</h2><p>DRF 提供了丰富的认证和权限机制，实际项目中建议结合 JWT 使用。</p>',
 'https://picsum.photos/seed/django-drf/800/400',
 'published', 2156, 134, 9, 1, '11111111111141118111111111111111',
 '2026-05-03 10:00:00.000000', '2026-05-03 09:00:00.000000', '2026-05-05 11:00:00.000000'),

-- 文章 3
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03',
 'Vue 3 Composition API 完全指南',
 'vue3-composition-api-guide',
 '从 Options API 到 Composition API，详解 Vue 3 的 setup、ref、reactive、computed、watch 等核心 API。',
 '# Vue 3 Composition API 完全指南\n\n## 为什么选择 Composition API？\n\nOptions API 在小型组件中工作良好，但随着组件逻辑的增长，代码按选项（data、methods、computed）分散，维护变得困难。Composition API 允许按**逻辑关注点**组织代码。\n\n## setup 函数\n\n```javascript\nimport { ref, computed } from ''vue''\n\nexport default {\n  setup() {\n    const count = ref(0)\n    const doubled = computed(() => count.value * 2)\n    function increment() { count.value++ }\n    return { count, doubled, increment }\n  }\n}\n```\n\n## script setup 语法糖\n\nVue 3.2 引入了更简洁的写法：\n\n```vue\n<script setup>\nimport { ref } from ''vue''\nconst message = ref(''Hello Vue 3!'')\n</script>\n```',
 '<h1>Vue 3 Composition API 完全指南</h1><h2>为什么选择 Composition API？</h2><p>Composition API 允许按逻辑关注点组织代码。</p><h2>setup 函数</h2><pre><code>import { ref, computed } from ''vue''\n\nexport default {\n  setup() {\n    const count = ref(0)\n    const doubled = computed(() => count.value * 2)\n    return { count, doubled }\n  }\n}</code></pre>',
 'https://picsum.photos/seed/vue3-comp/800/400',
 'published', 3421, 210, 6, 1, '11111111111141118111111111111111',
 '2026-05-05 12:00:00.000000', '2026-05-05 11:00:00.000000', '2026-05-05 12:00:00.000000'),

-- 文章 4
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb04',
 'MySQL 索引优化：从 B+Tree 到实际应用',
 'mysql-index-optimization',
 '深入解析 MySQL InnoDB 的 B+Tree 索引结构，以及实际开发中如何利用 EXPLAIN 分析查询性能并优化索引。',
 '# MySQL 索引优化\n\n## B+Tree 索引结构\n\nInnoDB 使用 B+Tree 作为索引结构。与 B-Tree 不同，B+Tree 的所有数据都存储在**叶子节点**，内部节点仅存储键值用于路由。\n\n## 聚集索引与二级索引\n\n- **聚集索引**：以主键构建，叶子节点存储完整行数据\n- **二级索引**：叶子节点存储索引列 + 主键值，需要**回表**查询\n\n## EXPLAIN 实战\n\n```sql\nEXPLAIN SELECT * FROM article WHERE status = ''published'';\n```\n\n关注以下字段：\n- `type`：访问类型（const > eq_ref > ref > range > index > ALL）\n- `key`：实际使用的索引\n- `Extra`：额外信息，`Using filesort` 说明需要优化\n\n## 最佳实践\n\n1. 选择性高的列适合建索引\n2. 联合索引遵循最左前缀原则\n3. 避免在索引列上使用函数或运算',
 '<h1>MySQL 索引优化</h1><h2>B+Tree 索引结构</h2><p>InnoDB 使用 B+Tree 作为索引结构。所有数据都存储在叶子节点。</p><h2>EXPLAIN 实战</h2><pre><code>EXPLAIN SELECT * FROM article WHERE status = ''published'';</code></pre><h2>最佳实践</h2><ol><li>选择性高的列适合建索引</li><li>联合索引遵循最左前缀原则</li><li>避免在索引列上使用函数或运算</li></ol>',
 'https://picsum.photos/seed/mysql-idx/800/400',
 'published', 1876, 156, 5, 1, '11111111111141118111111111111111',
 '2026-05-07 08:00:00.000000', '2026-05-07 07:00:00.000000', '2026-05-08 16:00:00.000000'),

-- 文章 5
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05',
 'JavaScript Promise 与事件循环机制',
 'js-promise-event-loop',
 '彻底搞懂 JavaScript 的事件循环、宏任务、微任务以及 Promise 的执行机制，面试不再慌。',
 '# JavaScript Promise 与事件循环\n\n## 单线程的 JavaScript\n\nJavaScript 是单线程语言，但通过事件循环机制实现了异步非阻塞。\n\n## 宏任务与微任务\n\n- **宏任务**：setTimeout、setInterval、I/O\n- **微任务**：Promise.then、MutationObserver、queueMicrotask\n\n```javascript\nconsole.log(''1'');\n\nsetTimeout(() => console.log(''2''), 0);\n\nPromise.resolve().then(() => console.log(''3''));\n\nconsole.log(''4'');\n\n// 输出顺序：1 → 4 → 3 → 2\n```\n\n## 执行顺序\n\n1. 执行同步代码（调用栈）\n2. 清空微任务队列\n3. 执行一个宏任务\n4. 重复步骤 2-3',
 '<h1>JavaScript Promise 与事件循环</h1><h2>单线程的 JavaScript</h2><p>JavaScript 是单线程语言，但通过事件循环机制实现了异步非阻塞。</p><h2>宏任务与微任务</h2><pre><code>console.log(''1'');\nsetTimeout(() => console.log(''2''), 0);\nPromise.resolve().then(() => console.log(''3''));\nconsole.log(''4'');\n// 输出：1 → 4 → 3 → 2</code></pre>',
 'https://picsum.photos/seed/js-promise/800/400',
 'published', 2890, 178, 8, 1, '11111111111141118111111111111111',
 '2026-05-09 14:00:00.000000', '2026-05-09 13:00:00.000000', '2026-05-09 14:00:00.000000'),

-- 文章 6
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb06',
 '用 Docker 容器化你的 Django 应用',
 'dockerize-django-app',
 '从 Dockerfile 编写到 docker-compose 编排，完整的 Django + MySQL + Redis 容器化部署方案。',
 '# 用 Docker 容器化 Django 应用\n\n## 为什么需要容器化？\n\n容器化解决了"在我机器上能跑"的问题，确保开发、测试、生产环境一致。\n\n## Dockerfile\n\n```dockerfile\nFROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nEXPOSE 8000\nCMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]\n```\n\n## docker-compose.yml\n\n```yaml\nservices:\n  web:\n    build: .\n    ports:\n      - "8000:8000"\n    depends_on:\n      - db\n  db:\n    image: mysql:8.0\n    environment:\n      MYSQL_DATABASE: zblog\n      MYSQL_ROOT_PASSWORD: secret\n```',
 '<h1>用 Docker 容器化 Django 应用</h1><h2>为什么需要容器化？</h2><p>容器化确保开发、测试、生产环境一致。</p><h2>Dockerfile</h2><pre><code>FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt</code></pre>',
 'https://picsum.photos/seed/docker-django/800/400',
 'published', 987, 67, 4, 1, '11111111111141118111111111111111',
 '2026-05-10 16:00:00.000000', '2026-05-10 15:00:00.000000', '2026-05-10 16:00:00.000000'),

-- 文章 7
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07',
 '我的 2025 年技术书单推荐',
 '2025-tech-books',
 '盘点 2025 年读过的最值得推荐的技术书籍，涵盖编程语言、系统设计、个人成长等多个方向。',
 '# 我的 2025 年技术书单推荐\n\n## 编程语言\n\n1. **《Fluent Python》第二版** — 深入 Python 内部机制，适合有一定基础的开发者\n2. **《Rust 程序设计》** — Rust 官方的入门教程，质量很高\n\n## 系统设计\n\n3. **《Designing Data-Intensive Applications》** — 经典之作，常读常新\n4. **《凤凰架构》** — 从单体到微服务架构的演进之路\n\n## 个人成长\n\n5. **《软技能：代码之外的生存指南》** — 程序员也需要关注的职场和个人发展\n\n> 读书不在多，在于精。一本好书值得反复阅读。',
 '<h1>我的 2025 年技术书单推荐</h1><h2>编程语言</h2><ol><li><strong>《Fluent Python》第二版</strong> — 深入 Python 内部机制</li><li><strong>《Rust 程序设计》</strong> — Rust 官方入门教程</li></ol><h2>系统设计</h2><ol start="3"><li><strong>《Designing Data-Intensive Applications》</strong> — 经典之作</li></ol>',
 'https://picsum.photos/seed/tech-books/800/400',
 'published', 1567, 245, 6, 1, '22222222222242228222222222222222',
 '2026-05-11 10:00:00.000000', '2026-05-11 09:00:00.000000', '2026-05-11 10:00:00.000000'),

-- 文章 8
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08',
 '如何搭建个人博客：技术选型与部署实践',
 'build-personal-blog',
 '从零开始搭建个人博客的完整记录，包括 Django 后端 + Vue 前端的架构设计和部署经验分享。',
 '# 如何搭建个人博客\n\n## 动机\n\n拥有一个完全属于自己的博客平台，不受第三方限制，可以自由定制功能和样式。\n\n## 技术选型\n\n| 层级 | 技术 |\n|------|------|\n| 后端框架 | Django 6 + DRF |\n| 前端框架 | Vue 3 + Vite |\n| 数据库 | MySQL 8.0 |\n| 部署 | Docker + Nginx |\n\n## 核心功能\n\n- Markdown 编辑器 + 实时预览\n- 标签和分类管理\n- 评论系统\n- RSS 订阅\n\n## 部署\n\n使用 GitHub Actions 实现 CI/CD，push 代码后自动构建并部署到服务器。',
 '<h1>如何搭建个人博客</h1><h2>技术选型</h2><table><tr><th>层级</th><th>技术</th></tr><tr><td>后端框架</td><td>Django 6 + DRF</td></tr><tr><td>前端框架</td><td>Vue 3 + Vite</td></tr></table><h2>核心功能</h2><ul><li>Markdown 编辑器</li><li>标签和分类管理</li><li>评论系统</li></ul>',
 'https://picsum.photos/seed/blog-build/800/400',
 'published', 4320, 312, 10, 1, '22222222222242228222222222222222',
 '2026-05-12 08:00:00.000000', '2026-05-12 07:00:00.000000', '2026-05-13 09:00:00.000000'),

-- 文章 9
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb09',
 '用 Git 高效管理代码：团队协作最佳实践',
 'git-team-best-practices',
 '总结团队协作中 Git 的最佳实践，包括分支策略、Commit 规范、Code Review 流程等。',
 '# Git 团队协作最佳实践\n\n## 分支策略\n\n推荐使用 **Trunk-Based Development** 或简化版的 Git Flow：\n\n- `main` — 生产分支，保持稳定\n- `develop` — 开发分支\n- `feature/xxx` — 功能分支\n\n## Commit 规范\n\n遵循 Conventional Commits：\n\n```\nfeat: 添加用户登录功能\nfix: 修复分页计算错误\nrefactor: 重构文章服务层\ndocs: 更新 API 文档\n```\n\n## Code Review\n\n- PR 保持小而聚焦（不超过 400 行变更）\n- 审查者应在 24 小时内完成 review\n- 关注逻辑正确性、安全性、可维护性',
 '<h1>Git 团队协作最佳实践</h1><h2>分支策略</h2><p>推荐使用 Trunk-Based Development：</p><ul><li>main — 生产分支</li><li>feature/xxx — 功能分支</li></ul><h2>Commit 规范</h2><pre><code>feat: 添加用户登录功能\nfix: 修复分页计算错误\nrefactor: 重构文章服务层</code></pre>',
 'https://picsum.photos/seed/git-team/800/400',
 'published', 876, 98, 4, 1, '11111111111141118111111111111111',
 '2026-05-13 11:00:00.000000', '2026-05-13 10:00:00.000000', '2026-05-13 11:00:00.000000'),

-- 文章 10
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10',
 '前端性能优化：从页面加载到交互响应',
 'frontend-performance-optimization',
 '系统梳理前端性能优化的核心指标（LCP、FID、CLS）和实战优化手段，提升用户体验。',
 '# 前端性能优化\n\n## Core Web Vitals\n\nGoogle 提出的核心性能指标：\n\n- **LCP（最大内容绘制）**：< 2.5 秒为优秀\n- **FID（首次输入延迟）**：< 100ms 为优秀\n- **CLS（累计布局偏移）**：< 0.1 为优秀\n\n## 优化手段\n\n### 资源加载\n\n- 图片使用 WebP 格式 + 懒加载\n- JS 按路由拆分（Code Splitting）\n- 关键 CSS 内联\n\n### 缓存策略\n\n```nginx\nlocation ~* \\.(js|css|png|jpg|webp)$ {\n    expires 1y;\n    add_header Cache-Control "public, immutable";\n}\n```\n\n### 减少重绘与回流\n\n- 使用 `transform` 代替 `top/left` 做动画\n- 批量修改 DOM（DocumentFragment）\n- 虚拟列表渲染大量数据',
 '<h1>前端性能优化</h1><h2>Core Web Vitals</h2><ul><li>LCP &lt; 2.5s 为优秀</li><li>FID &lt; 100ms 为优秀</li><li>CLS &lt; 0.1 为优秀</li></ul><h2>优化手段</h2><h3>资源加载</h3><p>图片使用 WebP 格式 + 懒加载，JS 按路由拆分。</p><h3>缓存策略</h3><pre><code>location ~* \\.(js|css|png|jpg|webp)$ {\n    expires 1y;\n}</code></pre>',
 'https://picsum.photos/seed/frontend-perf/800/400',
 'published', 1654, 143, 5, 1, '11111111111141118111111111111111',
 '2026-05-14 09:00:00.000000', '2026-05-14 08:00:00.000000', '2026-05-14 09:00:00.000000');

-- ============================================
-- 4. 文章-标签关联（M2M）
-- Django 自动生成的中间表名为 article_tags
-- ============================================
INSERT INTO `article_tags` (`article_id`, `tag_id`) VALUES
-- 文章 1: Python + 后端
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa1'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa7'),
-- 文章 2: Python + Django + 后端
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa1'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa2'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa7'),
-- 文章 3: JavaScript + Vue + 前端
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa3'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa4'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa6'),
-- 文章 4: 数据库 + 后端
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb04', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa5'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb04', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa7'),
-- 文章 5: JavaScript + 前端
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa3'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa6'),
-- 文章 6: Python + Django + DevOps
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb06', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa1'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb06', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa2'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb06', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa8'),
-- 文章 7: 后端 + 前端
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa7'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa6'),
-- 文章 8: Python + Django + Vue + DevOps
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa1'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa2'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa4'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa8'),
-- 文章 9: 后端 + DevOps
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb09', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa7'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb09', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa8'),
-- 文章 10: JavaScript + Vue + 前端
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa3'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa4'),
('bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10', 'aaaaaaaaaaaa4aaa8aaaaaaaaaaaaaa6');

-- ============================================
-- 5. 评论（每篇文章 4-10 条，含嵌套回复）
-- ============================================
INSERT INTO `article_comment` (`id`, `article_id`, `author_id`, `parent_id`, `content`, `created_at`, `updated_at`) VALUES

-- === 文章 1 的评论（7 条） ===
('c0000001000140008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01', 1, NULL,
 '写得很好！异步编程一直是 Python 新手的痛点，这篇文章讲得很清楚。',
 '2026-05-01 10:00:00.000000', '2026-05-01 10:00:00.000000'),
('c0000001000140008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01', 1, 'c0000001000140008000000000000001',
 '同感，我之前一直搞不懂 asyncio，看了文章豁然开朗。',
 '2026-05-01 11:00:00.000000', '2026-05-01 11:00:00.000000'),
('c0000001000140008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01', 1, NULL,
 '能再出一篇关于 asyncio 和 trio 对比的文章吗？想了解一下各自的优劣。',
 '2026-05-01 14:00:00.000000', '2026-05-01 14:00:00.000000'),
('c0000001000140008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01', 1, NULL,
 '代码示例很清晰，收藏了！',
 '2026-05-02 08:00:00.000000', '2026-05-02 08:00:00.000000'),
('c0000001000140008000000000000005', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01', 1, NULL,
 '请问在实际项目中，FastAPI 和 Django 的异步支持，你更推荐哪个？',
 '2026-05-02 15:00:00.000000', '2026-05-02 15:00:00.000000'),
('c0000001000140008000000000000006', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01', 1, 'c0000001000140008000000000000005',
 '个人觉得看场景，如果纯 API 服务 FastAPI 更轻量，需要完整框架生态选 Django。',
 '2026-05-02 16:00:00.000000', '2026-05-02 16:00:00.000000'),
('c0000001000140008000000000000007', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01', 1, NULL,
 '建议增加一个关于 asyncio.gather 和 asyncio.create_task 区别的章节。',
 '2026-05-03 09:00:00.000000', '2026-05-03 09:00:00.000000'),

-- === 文章 2 的评论（9 条） ===
('c0000002000240008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 1, NULL,
 'DRF 确实是 Django 生态里最成熟的 REST 框架了，文章总结得很全面。',
 '2026-05-03 12:00:00.000000', '2026-05-03 12:00:00.000000'),
('c0000002000240008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 1, NULL,
 '关于认证部分可以展开讲讲 JWT 的使用吗？',
 '2026-05-03 13:00:00.000000', '2026-05-03 13:00:00.000000'),
('c0000002000240008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 1, 'c0000002000240008000000000000002',
 '你可以看看 djangorestframework-simplejwt 这个库，集成起来很方便。',
 '2026-05-03 14:00:00.000000', '2026-05-03 14:00:00.000000'),
('c0000002000240008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 1, NULL,
 '在实际项目中，你们是怎么处理序列化器嵌套的性能问题的？',
 '2026-05-04 09:00:00.000000', '2026-05-04 09:00:00.000000'),
('c0000002000240008000000000000005', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 1, NULL,
 '好文！已转发给团队。',
 '2026-05-04 10:00:00.000000', '2026-05-04 10:00:00.000000'),
('c0000002000240008000000000000006', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 1, NULL,
 'ViewSet 和 generics 怎么选择？有些场景感觉 ViewSet 太重了。',
 '2026-05-04 15:00:00.000000', '2026-05-04 15:00:00.000000'),
('c0000002000240008000000000000007', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 1, 'c0000002000240008000000000000006',
 '简单的 CRUD 用 ViewSet，复杂业务逻辑用 generics + 手动写 action，灵活度更高。',
 '2026-05-04 16:00:00.000000', '2026-05-04 16:00:00.000000'),
('c0000002000240008000000000000008', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 1, NULL,
 '文章里的代码示例可以直接拿来用，省了不少时间。',
 '2026-05-05 08:00:00.000000', '2026-05-05 08:00:00.000000'),
('c0000002000240008000000000000009', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02', 1, NULL,
 '希望能加上关于 API 版本管理的内容。',
 '2026-05-05 10:00:00.000000', '2026-05-05 10:00:00.000000'),

-- === 文章 3 的评论（6 条） ===
('c0000003000340008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03', 1, NULL,
 '从 Options API 转到 Composition API 之后代码组织确实清晰多了。',
 '2026-05-05 14:00:00.000000', '2026-05-05 14:00:00.000000'),
('c0000003000340008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03', 1, NULL,
 'script setup 是真的香，写起来太舒服了。',
 '2026-05-05 15:00:00.000000', '2026-05-05 15:00:00.000000'),
('c0000003000340008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03', 1, 'c0000003000340008000000000000002',
 '确实，模板里直接用顶层变量，比 return 一堆东西优雅多了。',
 '2026-05-05 16:00:00.000000', '2026-05-05 16:00:00.000000'),
('c0000003000340008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03', 1, NULL,
 'watchEffect 和 watch 的区别讲得不太清楚，能再补充一下吗？',
 '2026-05-06 09:00:00.000000', '2026-05-06 09:00:00.000000'),
('c0000003000340008000000000000005', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03', 1, NULL,
 '推荐配合 Pinia 使用，状态管理非常丝滑。',
 '2026-05-06 10:00:00.000000', '2026-05-06 10:00:00.000000'),
('c0000003000340008000000000000006', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03', 1, NULL,
 '期待出续集讲讲组合式函数的封装技巧。',
 '2026-05-06 11:00:00.000000', '2026-05-06 11:00:00.000000'),

-- === 文章 4 的评论（5 条） ===
('c0000004000440008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb04', 1, NULL,
 'B+Tree 的图解很直观，终于理解了聚集索引和二级索引的区别。',
 '2026-05-07 10:00:00.000000', '2026-05-07 10:00:00.000000'),
('c0000004000440008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb04', 1, NULL,
 '最左前缀原则是面试高频考点，建议大家都认真看看。',
 '2026-05-07 12:00:00.000000', '2026-05-07 12:00:00.000000'),
('c0000004000440008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb04', 1, NULL,
 '我们项目之前有个慢查询，用 EXPLAIN 分析后发现没走索引，加了联合索引后快了 100 倍。',
 '2026-05-08 08:00:00.000000', '2026-05-08 08:00:00.000000'),
('c0000004000440008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb04', 1, 'c0000004000440008000000000000003',
 '100 倍！能分享一下具体的 SQL 和优化过程吗？',
 '2026-05-08 09:00:00.000000', '2026-05-08 09:00:00.000000'),
('c0000004000440008000000000000005', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb04', 1, NULL,
 '覆盖索引那块可以再展开讲讲，用具体的例子说明什么时候不需要回表。',
 '2026-05-08 14:00:00.000000', '2026-05-08 14:00:00.000000'),

-- === 文章 5 的评论（8 条） ===
('c0000005000540008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 1, NULL,
 '事件循环是 JS 核心中的核心，这篇文章讲解得非常到位。',
 '2026-05-09 15:00:00.000000', '2026-05-09 15:00:00.000000'),
('c0000005000540008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 1, NULL,
 '面试被问了三次事件循环，每次都答不全，早点看到这篇文章就好了。',
 '2026-05-09 16:00:00.000000', '2026-05-09 16:00:00.000000'),
('c0000005000540008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 1, NULL,
 'async/await 其实就是 Generator + Promise 的语法糖，之前一直没想明白这个关系。',
 '2026-05-10 08:00:00.000000', '2026-05-10 08:00:00.000000'),
('c0000005000540008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 1, NULL,
 '宏任务微任务的执行顺序面试必问，但实际开发中遇到的坑才是真让人头疼的。',
 '2026-05-10 09:00:00.000000', '2026-05-10 09:00:00.000000'),
('c0000005000540008000000000000005', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 1, 'c0000005000540008000000000000004',
 '确实，有次在 forEach 里用 async/await 结果不符合预期，排查了半天才发现 forEach 不会等 await。',
 '2026-05-10 10:00:00.000000', '2026-05-10 10:00:00.000000'),
('c0000005000540008000000000000006', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 1, NULL,
 '文章写得不错，建议加一个关于 requestAnimationFrame 在事件循环中位置的说明。',
 '2026-05-10 11:00:00.000000', '2026-05-10 11:00:00.000000'),
('c0000005000540008000000000000007', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 1, NULL,
 'queueMicrotask 这个 API 也是最近才关注到的，很好用。',
 '2026-05-10 12:00:00.000000', '2026-05-10 12:00:00.000000'),
('c0000005000540008000000000000008', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05', 1, NULL,
 '收藏了，每次面试前都翻一遍。',
 '2026-05-10 13:00:00.000000', '2026-05-10 13:00:00.000000'),

-- === 文章 6 的评论（4 条） ===
('c0000006000640008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb06', 1, NULL,
 'Docker 确实解决了环境一致性问题，再也不用在服务器上手动装依赖了。',
 '2026-05-10 17:00:00.000000', '2026-05-10 17:00:00.000000'),
('c0000006000640008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb06', 1, NULL,
 'docker-compose 的 depends_on 只是控制启动顺序，不保证服务已经就绪，这里容易踩坑。',
 '2026-05-11 08:00:00.000000', '2026-05-11 08:00:00.000000'),
('c0000006000640008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb06', 1, 'c0000006000640008000000000000002',
 '对的，最好用 wait-for-it.sh 或者 healthcheck 来确保服务可用。',
 '2026-05-11 09:00:00.000000', '2026-05-11 09:00:00.000000'),
('c0000006000640008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb06', 1, NULL,
 '多阶段构建可以显著减小镜像体积，建议在文章里提一下。',
 '2026-05-11 10:00:00.000000', '2026-05-11 10:00:00.000000'),

-- === 文章 7 的评论（6 条） ===
('c0000007000740008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07', 1, NULL,
 'DDIA 真的是神作，每年读一遍都有新的理解。',
 '2026-05-11 12:00:00.000000', '2026-05-11 12:00:00.000000'),
('c0000007000740008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07', 1, NULL,
 '《凤凰架构》也很不错，对理解分布式系统帮助很大。',
 '2026-05-11 13:00:00.000000', '2026-05-11 13:00:00.000000'),
('c0000007000740008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07', 1, NULL,
 '再加一本《重构：改善既有代码的设计》，提升代码质量的必读书。',
 '2026-05-11 14:00:00.000000', '2026-05-11 14:00:00.000000'),
('c0000007000740008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07', 1, NULL,
 'Fluent Python 第二版比第一版增加了不少内容，强烈推荐。',
 '2026-05-12 08:00:00.000000', '2026-05-12 08:00:00.000000'),
('c0000007000740008000000000000005', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07', 1, 'c0000007000740008000000000000004',
 '第二版的 asyncio 章节写得特别精彩，连 Guido 都给了好评。',
 '2026-05-12 09:00:00.000000', '2026-05-12 09:00:00.000000'),
('c0000007000740008000000000000006', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07', 1, NULL,
 '期待 2026 年的书单推荐！',
 '2026-05-12 10:00:00.000000', '2026-05-12 10:00:00.000000'),

-- === 文章 8 的评论（10 条） ===
('c0000008000840008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, NULL,
 '最近也在搭个人博客，这篇来得太及时了！',
 '2026-05-12 10:00:00.000000', '2026-05-12 10:00:00.000000'),
('c0000008000840008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, NULL,
 '为什么不直接用静态博客（如 Hexo/Hugo），而要用 Django + Vue 这样重的方案？',
 '2026-05-12 11:00:00.000000', '2026-05-12 11:00:00.000000'),
('c0000008000840008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, 'c0000008000840008000000000000002',
 '动态博客的好处是可以加评论、全文搜索、后台管理等交互功能，自由度更高。静态博客部署简单但扩展性有限。',
 '2026-05-12 12:00:00.000000', '2026-05-12 12:00:00.000000'),
('c0000008000840008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, NULL,
 'Nginx 反向代理那块能再详细讲讲吗？我配置的时候老是遇到 502。',
 '2026-05-12 14:00:00.000000', '2026-05-12 14:00:00.000000'),
('c0000008000840008000000000000005', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, NULL,
 '域名和 HTTPS 怎么配置的？用的 Let''s Encrypt 免费证书吗？',
 '2026-05-12 15:00:00.000000', '2026-05-12 15:00:00.000000'),
('c0000008000840008000000000000006', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, 'c0000008000840008000000000000005',
 'Certbot + Let''s Encrypt 就可以，一行命令搞定，而且支持自动续签。',
 '2026-05-12 16:00:00.000000', '2026-05-12 16:00:00.000000'),
('c0000008000840008000000000000007', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, NULL,
 '文章写得很好，我按这个方案搭了一个周末就搞定了。',
 '2026-05-13 08:00:00.000000', '2026-05-13 08:00:00.000000'),
('c0000008000840008000000000000008', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, NULL,
 'RSS 订阅功能怎么实现的？是用 Django 的那个 RSS 插件吗？',
 '2026-05-13 09:00:00.000000', '2026-05-13 09:00:00.000000'),
('c0000008000840008000000000000009', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, NULL,
 '请问评论系统有没有做反垃圾处理？最近被机器人评论轰炸了。',
 '2026-05-13 10:00:00.000000', '2026-05-13 10:00:00.000000'),
('c0000008000840008000000000000010', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08', 1, NULL,
 '已收藏，等有空了跟着搭一遍。',
 '2026-05-13 11:00:00.000000', '2026-05-13 11:00:00.000000'),

-- === 文章 9 的评论（4 条） ===
('c0000009000940008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb09', 1, NULL,
 'Conventional Commits 我们团队也在用，配合 commitlint 自动检查格式，效果很好。',
 '2026-05-13 12:00:00.000000', '2026-05-13 12:00:00.000000'),
('c0000009000940008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb09', 1, NULL,
 'PR 不超过 400 行这个建议很实用，之前一个大 PR 改了 2000 多行，review 到崩溃。',
 '2026-05-13 14:00:00.000000', '2026-05-13 14:00:00.000000'),
('c0000009000940008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb09', 1, 'c0000009000940008000000000000002',
 '确实，小 PR 的好处是 review 质量高、合并快、出问题也容易定位和回滚。',
 '2026-05-13 15:00:00.000000', '2026-05-13 15:00:00.000000'),
('c0000009000940008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb09', 1, NULL,
 '请问有没有推荐的可视化 Git 工具？命令行用久了想换换口味。',
 '2026-05-13 16:00:00.000000', '2026-05-13 16:00:00.000000'),

-- === 文章 10 的评论（5 条） ===
('c0000010001040008000000000000001', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10', 1, NULL,
 'Lighthouse 跑分从 60 提到 95，按这篇文章优化了一遍，效果显著。',
 '2026-05-14 10:00:00.000000', '2026-05-14 10:00:00.000000'),
('c0000010001040008000000000000002', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10', 1, NULL,
 'CLS 这个问题很隐蔽，很多页面功能正常但用户体验很差就是因为布局偏移。',
 '2026-05-14 11:00:00.000000', '2026-05-14 11:00:00.000000'),
('c0000010001040008000000000000003', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10', 1, NULL,
 'WebP 格式兼容性现在基本没问题了，Safari 从 14 版本开始就支持了。',
 '2026-05-14 12:00:00.000000', '2026-05-14 12:00:00.000000'),
('c0000010001040008000000000000004', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10', 1, 'c0000010001040008000000000000003',
 '还可以考虑 AVIF，压缩率更高，不过兼容性稍差一点。',
 '2026-05-14 13:00:00.000000', '2026-05-14 13:00:00.000000'),
('c0000010001040008000000000000005', 'bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10', 1, NULL,
 '虚拟列表这块可以展开讲讲，对于长列表优化确实很重要。',
 '2026-05-14 14:00:00.000000', '2026-05-14 14:00:00.000000');
