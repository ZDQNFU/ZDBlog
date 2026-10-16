# 博客知识库 RAG 实现文档

> 撰写日期：2026-10-03
> 目标读者：实现这套 RAG 的后端开发者（熟悉 Django，未做过检索系统）
> 适用代码：`zdblog-master`（Django 6 + PostgreSQL 17 + pgvector + LangChain 1.3）

> **2026-10-03 实现审查与修正**：原方案可行，但以下骨架不是最终代码，使用时请以新增 [RAG 运行说明](../zdblog-master/rag/readme.md) 为准。实际采用用户已有的 `BAAI/bge-small-zh-v1.5` 本地缓存，**512 维**、CPU 离线推理，复用既有 Python 推理环境的常驻 worker；不再要求配置在线 embedding 密钥。下文 BGE-M3 / 1024 维是原始选型记录。
>
> 审查发现并已在实现中修正的问题：
> 1. top-k 无相关性过滤必然返回最近邻，不能通过“站内没有该话题”的负例。现在先应用可调相关性门槛，再融合；门槛须用金标集校准，未命中只能表示“本次未找到”，不能证明文章不存在。
> 2. 对 400 字正文使用整段 `similarity()` 和默认 `%` 阈值会漏掉短术语。现在使用 `word_similarity()`、子串匹配和查询词拆分，两路仍过滤 `published`。参考 [PostgreSQL pg_trgm 文档](https://www.postgresql.org/docs/17/pgtrgm.html)。
> 3. 内容 hash 不能识别 embedding 模型变更；NumPy 向量 `if c.embedding` 会触发 ambiguous truth value。实现通过 SQL `IS NOT NULL`、模型指纹和源版本 hash 分别处理复用、模型空间及过期正文。
> 4. 网络 embedding 结束前文章可能被再次编辑或撤回。现在网络调用在事务外，替换块时锁定文章并复核版本；检索再次核对源 hash，批量更新也不会返回旧正文。
> 5. `on_commit` 直接抛异常会造成“文章已保存但接口失败”。同步回调捕获失败，保存错误状态；词法查询使用 savepoint，避免 SQL 失败破坏外层事务。
> 6. `tool_names or DEFAULT_TOOLS` 无法表达空工具列表。现在只有 `None` 使用默认值，`[]` 明确关闭工具；后台可配置、会话保存快照。
> 7. 返回文本硬截断会截掉引用链接；实现按完整出处分配预算，保留链接并按文章去重。1,500 字不是 2 KB，中文 UTF-8 及 JSON 开销要另算。
> 8. `rag_eval` 原脚本的 Recall 实际是 HitRate。现在分别输出 article-level Recall、HitRate、MRR 和负例正确率，金标路径从项目目录解析。
> 9. 将已有 `vector(1024)` 直接转换成 `vector(1536)` 会因旧值维度错误而失败。迁移维度必须先停用旧向量/清空派生 embedding，写 Django schema 迁移，再全量重建；不可只改环境变量。此次新增表直接使用 `vector(512)`。
> 10. 保留短小章节，避免静默丢掉关键事实；长代码围栏保护和 rerank 尚未实现，属于后续可量化优化。
> 11. 原金标将“我写过 Rust 的什么内容”标为无命中，但现有书单正文明确推荐《Rust 程序设计》。已修正为书单正例，并加入正文未覆盖的 WebRTC ICE 问题作为负例。当前金标共 10 个正例、3 个负例。
>
> 本地模型的 query instruction 与归一化参考 [BAAI 模型卡](https://huggingface.co/BAAI/bge-small-zh-v1.5)。新增 `rag` 应用、命令、人物工具配置及数据库迁移已经实现；评估结果与操作步骤见运行说明。

本文是一份**可照着做**的实现文档：包含选型结论与理由、数据模型、代码骨架、分阶段落地步骤、验收标准，以及本项目特有的坑。

外部 API 的结论（哪家提供 embedding、模型维度）请在实际选型时复核一次，其余关于本仓库的事实均已在 2026-10-03 实测确认。

> **§2.4 的前置已于 2026-10-03 做完了**：本机库 `zblog` 里有 pgvector **0.8.7** 与 pg_trgm **1.6**，conda 环境里有 Python 包 `pgvector` **0.5.0**。直接从 §5 开始即可。
> §2.4 保留了完整的安装过程（含本机实测踩到的坑），供**换机器、重装、或部署到新环境**时照做——尤其是 Windows 上必须自己编译这一点，不写下来下次还得重新踩一遍。

---

## 0. 一句话方案

新增 `rag` 应用：把已发布文章切成带标题路径的块 → 用 OpenAI 兼容端点算 embedding（默认 BGE-M3，1024 维）→ 向量用 **pgvector** 的 `vector` 类型存进 PostgreSQL → 检索时**在 SQL 里**按余弦距离取 top-k（配 `pg_trgm` 做词法召回，RRF 融合）→ 包装成 `search_blog` 工具挂到现有 LangGraph agent 上。

**相比上一版（向量存 MySQL 的 `BinaryField` + 进程内 numpy 暴力检索），新增的依赖只有一个数据库扩展和它的 Python 包**：扩展 `vector`（§2.4，本机已装 0.8.7），Python 包 `pgvector`（纯 Python，`pip install` 即可，无编译，已装 0.5.0）。

选 pgvector 而不是内存索引，**主要收益不是快，而是删掉了一整类必须自己维护的状态**：不再有进程内矩阵、不再有 `invalidate()`、不再有"gunicorn 多 worker 各持一份旧索引"的问题、不再需要 `MAX(updated_at)` 版本探测。代价是多一个安装前置（见 §4.1 的对照表）。

---

## 1. 范围

### 1.1 目标

1. 「博客助手」角色能基于站内文章回答，答案里的观点/细节来自文章正文，而不是模型记忆。
2. 回答带**可点击的出处**（文章标题 + 链接），用户可以自己核对。
3. 文章增删改后，索引能增量更新。
4. 检索效果可量化（金标集 + Recall@k），改动前后能对比。

### 1.2 明确不做

| 不做 | 原因 |
|---|---|
| 微调模型来灌知识 | 更新要重训、成本高、且会加重幻觉。知识放检索，风格才放微调 |
| GraphRAG / 知识图谱 | 用于跨文档推理，个人博客规模下收益为零，维护成本极高 |
| 多模态检索（图片/封面） | 正文是主要知识载体，先不做 |
| 跨用户私有知识库 | 本站文章是单一公开语料，没有多租户需求 |
| 把文章全文塞进 `agent_messages` | 见 §11 坑 6，会撑爆 JSONField 与上下文预算 |

---

## 2. 现状与实测环境

### 2.1 环境事实（2026-10-03 实测）

| 项 | 实测值 | 对方案的影响 |
|---|---|---|
| Python | 3.12.13（conda 环境 `zblog-master`） | — |
| Django | 6.0.5 | `pgvector.django.VectorExtension` 对 Django ≥ 6 有专门分支，版本正好 |
| PostgreSQL | **17.11**，`x86_64-windows, compiled by msvc-19.44.3`，超管角色 `root`，库 `zblog`，端口 5432 | 目标库。2026-10-03 已从 MySQL 8.0.18 迁移完成 |
| **pgvector** | ✅ **0.8.7 已装**（本机源码编译，见 §2.4） | 向量存储与检索的核心，已就绪 |
| `pg_trgm` | ✅ **1.6 已 `CREATE EXTENSION`**（原生自带） | 词法召回腿用它做中文子串检索，替代原来的 MySQL ngram |
| 其他可用扩展 | `btree_gin` 1.3、`fuzzystrmatch` 1.2、`unaccent` 1.1 | 备选，本项目用不上 |
| 已装扩展 | `vector` 0.8.7、`pg_trgm` 1.6、`plpgsql` | 2026-10-03 装齐，见 §2.4 |
| Redis | **3.0.504**（Windows 老版本，standalone） | `MODULE`/`FT.SEARCH` 都不存在 → **不能拿它做向量检索**（Redis Stack / Redis 8 才行） |
| 已装依赖 | `langchain_text_splitters` ✅ `langgraph` ✅ `langchain_openai` ✅ `openai` ✅ `numpy` ✅ | 切块 / agent / embedding 链路无需新增依赖 |
| 未装 | `sentence_transformers` `qdrant_client` `jieba` `rank_bm25` `sklearn` | 方案设计为不依赖这些；`pgvector`（Python 包，0.5.0）已装 |

> **`numpy` 从"检索核心依赖"降级为"可选"**：向量运算全部下推给数据库之后，Python 侧不再需要矩阵库。
> 留着它不影响什么（`openmeteo-requests` 等会传递装上），但**别再把 numpy 写进 RAG 的必需依赖**——
> 上一版是必需的，这一版不是。

LLM 侧：`chat_robot/utils.py` 用 `ChatOpenAI` 指向 DeepSeek。**DeepSeek 官方未提供 embedding 接口**，所以 embedding 必须另配一家（见 §4.2）。

### 2.2 语料规模（实测，别跳过这一节）

| 指标 | 实测 |
|---|---|
| 已发布文章 | **9 篇** |
| 已发布正文总字数 | **4,197 字**（约 3k token） |
| 最长单篇 | 828 字 |
| 非公开文章 | 1 篇 private（338 字，**必须排除在索引外**） |

**这个规模下，全站正文一次塞进 prompt 也才 ~3k token，DeepSeek 的 128k 上下文能装 40 份。** 所以：

- 如果你的目标只是"能回答问题"，**Phase 0 + Phase 1 就够了**（见 §6），不必上向量。
- 本文的完整方案在 9 篇时也能跑（增量成本几分钱、检索延迟 +50ms 量级），现在做不算浪费，但**收益主要体现在"引用可追溯"和"以后不用返工"**，而不是召回质量。
- 阈值参考：

| 语料规模 | 建议 |
|---|---|
| < 30 篇 / < 5 万字 | 全量注入上下文，或纯 SQL 关键词检索（Phase 0+1） |
| 30 ~ 500 篇 | **本文方案**（pgvector 向量 + pg_trgm 词法，RRF 混合） |
| > 500 篇 / > 5 万 chunk | **仍然留在 pgvector**——建 HNSW 索引（§4.6），百万级以内都撑得住。加 rerank，再考虑并行 |
| > 百万级 chunk，或需要复杂 payload filter | 才轮到 Qdrant / Milvus。`rag/store.py` 是唯一要换的模块（§7.3） |

> 上一版这条分界线画在"500 篇 / 5 万 chunk 就换 Qdrant"，那是**内存索引方案**的极限（矩阵要整份进内存、且要自己维护失效）。换成 pgvector 后这个约束消失了，别把旧阈值照搬过来。

### 2.3 现有代码入口

| 位置 | 说明 |
|---|---|
| [chat_robot/agent.py](../zdblog-master/chat_robot/agent.py) | `build_agent(system_prompt)`，`create_agent(model, system_prompt, tools=[get_weather, search_func], middleware=[...])` |
| [chat_robot/tools.py](../zdblog-master/chat_robot/tools.py) | `@tool` 装饰的工具集合，中文 docstring（**docstring 就是给模型看的 prompt**） |
| [chat_robot/views.py](../zdblog-master/chat_robot/views.py) | `ChatStreamView` 流式对话；`generation_id` 是 15 分钟乐观锁租约 |
| [chat_robot/models.py](../zdblog-master/chat_robot/models.py) | `ChatPersona`（**没有工具配置字段**）、`ChatConversation`（快照字段 `persona_name`/`system_prompt`/`greeting`，`persona` 外键 `SET_NULL`）、`agent_messages = JSONField` |
| [article/models.py](../zdblog-master/article/models.py) | `Article`：`content_md`（Markdown 源）、`content_html`、`status`（draft/published/private）、`tags` M2M、`category` FK、`published_at` |
| [article/views/c_views.py](../zdblog-master/article/views/c_views.py) | 文章详情：`/api/articles/c/<id>/`，路由 `/article/:id`（**引用链接用 id，不是 slug**） |
| `tools/generate_nums.py` | `generate_uuid7`，全项目主键生成器 |
| [zdblog-vue-c/src/utils/chatMarkdown.js](../zdblog-vue-c/src/utils/chatMarkdown.js) | 前端 Markdown 白名单：**允许 `<a>`（http/https/mailto，相对链接会解析成绝对 URL）**，不允许 `<img>` |

### 2.4 前置条件：pgvector（2026-10-03 已完成）

**状态：已装好，不必再做。** 库 `zblog` 里现在有 `vector 0.8.7` 与 `pg_trgm 1.6`，conda 环境
`zblog-master` 里有 Python 包 `pgvector 0.5.0`。§12 的前置三条已全部满足。

下面保留完整过程，供**换机器 / 重装 / 部署新环境**时照做，并记下本机实测踩到的坑。

#### 为什么 Windows 上要自己编译

EDB 官方的 Windows 安装器**不捆绑 pgvector**——装完 `pg_available_extensions` 里查不到 `vector`，
`pg_extension` 里只有 `plpgsql`。而 pgvector 官方**不提供 Windows 预编译二进制**。所以只有三条路：

| 路径 | 前提 | 下载量 | 一次性耗时 | 评价 |
|---|---|---|---|---|
| **A. 本机编译**（本机采用） | 装 VS 2022 生成工具 | ~2–4 GB | 30–60 min | **保住这套原生集群**（`C:\Program Files\PostgreSQL\17`、端口 5432、服务 `postgresql-x64-17`），不引入新服务、不用起 Docker |
| **B. 改用 pgvector 的 Docker 镜像** | Docker Desktop 守护进程要开着 | ~400 MB 镜像 | 15 min | 下载量最小，但要把现有库**再搬一次家**，且以后开发都得先起 Docker |
| **C. 只在生产（Linux）装，本机继续用 numpy 内存索引** | — | 0 | — | **不推荐**：开发与生产跑两套检索实现，等于上线那套从来没被验证过 |

**A 路径可行的前提**（已实测确认，不是推测）：`include\server\postgres.h` ✅ 与
`lib\pgxs\src\makefiles\pgxs.mk` ✅ 都随 EDB 安装存在，所以**不需要额外下载 PostgreSQL 源码**，
只缺 MSVC 工具链。

#### A 路径的完整步骤（本机实跑通过）

```bat
:: 1. 装 VS 2022 生成工具，含 VCTools 工作负载
::    实测装出 17.14.41，cl.exe 为 14.44.35207
winget install --id Microsoft.VisualStudio.2022.BuildTools ^
  --override "--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --installPath C:\BuildTools"

:: 2. 用 vcvars64.bat 初始化环境。不必专门去开「x64 Native Tools Command Prompt」——
::    在普通 cmd 里 call 它效果一样，这样才能把整条流程写进脚本
call "C:\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

:: 3. 取源码。tag 用最新的 release，别用 main（v0.8.7 是 2026-10-03 实测的最新版）
git clone --branch v0.8.7 --depth 1 https://github.com/pgvector/pgvector.git
cd pgvector

:: 4. 编译。本机成功，产物 vector.dll = 281,088 字节
set "PGROOT=C:\Program Files\PostgreSQL\17"
nmake /F Makefile.win
```

> **MSVC 版本要对齐**。本机服务端是 `compiled by msvc-19.44.3`，即 VS 2022 (17.14) 的工具链。
> 用更老的 MSVC 编出的 DLL 加载进 `postgres.exe` 有 ABI 风险，**装 VS 2022，不要用 2019**。

**第 5 步「安装」不要用 `nmake install`。** 本机实测 `nmake /F Makefile.win install` **跑不起来**：
它在 `call vcvars64.bat` 之后**无声中断**——没有报错、没有退出码，日志里也没有任何 nmake 输出
（根因未查，不影响结果）。改用等价的纯拷贝脚本
[`data/pgvector-build/install-manual.bat`](../data/pgvector-build/install-manual.bat)，一次成功。

原因很简单：**"安装"本质上只是往 `C:\Program Files\PostgreSQL\17\` 里拷几个文件**，
根本不需要编译器参与：

| 从源码树 | 拷到 | 内容 |
|---|---|---|
| `vector.dll` | `lib\` | 扩展本体 |
| `vector.control` | `share\extension\` | 元数据：`default_version='0.8.7'`、`module_pathname='$libdir/vector'` |
| `sql\vector--*.sql` | `share\extension\` | 42 个安装/升级脚本 |
| `src\vector.h` `halfvec.h` `sparsevec.h` | `include\server\extension\vector\` | 头文件；只在"编译依赖它的其他扩展"时才需要，本项目可不拷 |

> **这一步必须提权。** `C:\Program Files\...` 当前用户没有写权限，得在管理员终端跑 `install-manual.bat`。
> 编译本身**不需要**管理员——把「编译」和「安装」拆成两个脚本，好处是编译错误能直接看见，
> 而且整个过程只需要一次 UAC。
>
> `install-manual.bat` 放在 `data/pgvector-build/`，而 `data/` 被 `.gitignore` 忽略，
> 所以它是**本机私有**的，不进版本库。换机器时照上表手工拷一遍即可。

#### 建扩展

装完在**每个**要用到的库上各执行一次（扩展是**按库**安装的，不是按集群）：

```sql
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- 词法召回腿要用，原生自带
```

验证扩展本身（不经过 Django、不经过任何应用代码）：

```sql
SELECT extname, extversion FROM pg_extension;         -- 应看到 vector 0.8.7 与 pg_trgm 1.6
SELECT '[1,2,3]'::vector <=> '[3,2,1]'::vector;       -- 余弦距离，应返回 0.2857142857142857
SELECT '[1,2,3]'::vector <-> '[3,2,1]'::vector;       -- L2 距离，应返回 2.8284271247461903
```

> **别把这两个数记混。** `<=>` 给的是 **0.2857…**（余弦距离，即 `1 - 10/14`）；**`2.8284…` 是 `<->` 的 L2 距离**。
> 网上不少例子把 `2.8284` 当成余弦距离的预期输出，那是错的——照着对会白白排查半天。

Python 侧：

```bash
pip install "pgvector>=0.3"    # 纯 Python（py3-none-any wheel），无编译、无 C 扩展
```

> **`pip install pgvector` 装的是什么、不装什么**：它只提供 Python 侧的 `VectorField` / `VectorExtension` /
> `HnswIndex` 和 psycopg 适配器，**完全不含数据库扩展**。数据库那边没 `CREATE EXTENSION vector`，
> `migrate` 会在建表时就报 `类型 "vector" 不存在`。**两边缺一不可。**

> **权限**：`CREATE EXTENSION` 需要**超级用户**。本机连库用的就是超管 `root`，所以 §5 那条迁移能直接跑过。
> 生产上如果应用连的是普通角色，这一步要由 DBA 预先执行一次——它属于"做一次就够"的初始化，
> 不该让应用账号在 `migrate` 里做（见 §10）。

---

## 3. 总体架构

```
【离线索引】python manage.py rag_reindex

  article.content_md (仅 status='published')
        │
        ├─ 1. 切块：Markdown 标题感知 + 递归切分，400 字/块、60 字重叠
        │     每块前缀 "《标题》 > 一级 > 二级"  ← 提升召回，块自带上下文
        ├─ 2. 算 hash：sha256(块正文)，比对已有块 → 只对新增/变更的块调 embedding
        ├─ 3. embedding：OpenAI 兼容端点（BGE-M3 / 1024 维）→ list[float]
        └─ 4. 写 article_chunk 表（vector(1024) 列，按文章粒度事务，避免中间态）

【在线检索】用户提问 → agent 决定调 search_blog(query)

  query ─┬─ 向量召回：ORDER BY embedding <=> $1 LIMIT 20     （pgvector）
         └─ 词法召回：pg_trgm 三元组相似度，取 top 20
                │
          RRF 融合 ─→ top 8 ─（可选 rerank）→ top 5
                │
          组装成 tool message：标题 + 章节 + 片段 + 链接（总长 ≤ 1500 字）
                │
          agent 基于片段作答，正文里带上 [《标题》](/article/<id>) 引用
```

注意 `status='published'` 的过滤在两条召回腿里都是 **SQL 的 `WHERE` 条件**，不是取回结果后再筛——
所以不存在"内存索引里还留着已改成 draft 的向量"这类问题（这正是上一版方案最大的隐患）。

**为什么用「工具」而不是「每轮自动检索注入」**：现有 agent 已经是工具调用架构（`tools=[...]`），走工具是一致的；且让模型自己决定"这问题要不要查站内文章"——问天气、问闲聊时不该触发检索。这就是 2025-2026 年主流的 **Agentic RAG**。

---

## 4. 关键决策

### 4.1 向量库：pgvector（PostgreSQL 扩展）

**结论：用 pgvector。** 向量就存在 `article_chunk` 表的一个 `vector(1024)` 列上，检索是一条带 `ORDER BY embedding <=> $1` 的 SQL。

不引入独立的向量数据库，也不在进程内维护矩阵。

**为什么改掉"进程内 numpy 暴力检索"**（这是本次修订的核心理由）——上一版把向量以 `float32` 字节存进 MySQL 的 `BinaryField`，检索时全量加载进内存算余弦。那个方案在**单进程、语料不变**时完全成立，但它强迫你自己维护一整套状态：

| 内存索引方案必须自己处理的事 | pgvector 方案 |
|---|---|
| 进程内矩阵要随语料重建；`invalidate()` 只能清掉当前进程的 | 没有矩阵，读的就是库里的当前值 |
| gunicorn 多 worker / `runserver` reload 各持一份，可能不同步 | 无状态，天然一致 |
| 靠 `MAX(updated_at)` 轮询做惰性刷新（原 §4.6） | 不需要 |
| `updated_at` 上要建索引，否则轮询退化成全表扫描 | 不需要 |
| 手动 `np.frombuffer` 还原字节，还要校验 `dim` 防脏数据 | 驱动与 `VectorField` 自动转换 `list[float] ↔ vector` |
| 状态过滤在 Python 里逐行判断，或取回后再复核 | 就是 SQL 的 `WHERE a.status = 'published'` |
| 换 embedding 模型后，旧维度的字节混在库里要靠代码跳过 | 列类型是 `vector(1024)`，写错维度**数据库当场报错** |

**代价**：多一个安装前置（§2.4），以及 Python 侧多一个纯 Python 包 `pgvector`（无编译）。

**关于 ANN 索引：本规模下不要建。** pgvector 支持 `hnsw` / `ivfflat` 索引，但**当前 11–30 个块，顺序扫描既精确又比走索引更快**——ANN 是近似算法，牺牲召回率换速度，几百行以内纯属净损失。判断依据与建索引语句见 §4.6。

**被否方案：**

- **Redis**：实测这台机器的 Redis 是 3.0.504，连 `MODULE` 命令都没有，`FT.SEARCH` 不存在。要用得先升级到 Redis Stack / Redis 8 并重建缓存层——为一个 8 MB 的矩阵不值得。
- **Qdrant / Milvus**：独立的向量服务。pgvector 在百万级 chunk 以下没有必须换的理由，而换它要多维护一个进程、一套备份、一个故障点。
- **内存索引（上一版方案）**：问题见上表。它的优势只在"零运维"上，而 pgvector 是**你已经在跑的数据库加一个扩展**，运维增量比它更小。

### 4.2 Embedding：OpenAI 兼容端点（默认 BGE-M3）

DeepSeek 没有 embedding 接口，必须另配。选型原则：**走 OpenAI 兼容的 `/v1/embeddings`**，这样直接用已装的 `langchain_openai.OpenAIEmbeddings`，零新增依赖。

| 方案 | 维度 | 评价 |
|---|---|---|
| **BGE-M3**（硅基流动等 OpenAI 兼容网关） | 1024 | **推荐默认**。中文效果好、支持 8192 长文本、按量计费便宜 |
| 阿里 DashScope `text-embedding-v3` | 1024（可选） | 国内稳定，SDK 非 OpenAI 协议时需要适配 |
| 智谱 `embedding-3` | 2048 | 备选 |
| OpenAI `text-embedding-3-small` | 1536 | 中文一般，且网络不通则不可用 |
| 本地 `BAAI/bge-m3`（sentence-transformers） | 1024 | 免费、数据不出内网，但要装 torch（Windows 上 ~2.5 GB），CPU 推理约 50 ms/块 |

**迁移成本几乎为零**：`RAG_EMBED_MODEL` / `RAG_EMBED_BASE_URL` / `RAG_EMBED_DIM` 三个配置项切换即可。**但换 embedding 模型必须全量重建索引**（不同模型的向量空间不可比），所以 `rag_reindex --force` 要能一键重建。

成本估算：正文 4,197 字 ≈ 3k token，全量索引一次不到 1 分钱；即使涨到 1000 篇文章（~35 万 token），单次全量重建也在角分级。

### 4.3 切块：Markdown 标题感知 + 标题路径前缀

- 先用 `MarkdownHeaderTextSplitter` 按 `#`~`####` 切，再对超长段落用 `RecursiveCharacterTextSplitter`（400 字、60 字重叠）。
- 每个块正文**前缀加上「《文章标题》 > 一级标题 > 二级标题」**。这一步（contextual prefix）是近年 RAG 实践里性价比最高的技巧之一：块脱离上下文后，"它"、"这个方法"这类指代会失效，加前缀能显著提升召回。
- **不要索引 `content_html`**：标签噪声大、代码块高亮 span 会污染文本。索引 `content_md`。
- 代码围栏（```）尽量不切断——被切一半的代码块会显著降低回答质量。简单做法：切块前把围栏块替换成占位符，切完再还原（本文档代码骨架未实现这层，作为 Phase 3 的优化项）。

### 4.4 检索：向量 + 词法 RRF 融合

- 单走向量：对"文章里那个用 F 表达式避免竞态的写法"这类语义提问好；对专有名词（`F()`、`B+Tree`、`pg_trgm`）反而容易漂。
- 单词法（`pg_trgm` 三元组相似度）：专有名词精准，但问"怎么避免计数器的并发问题"就抓瞎。
- **两者用 RRF（Reciprocal Rank Fusion）融合**：`score = Σ 1/(60 + rank)`。RRF 只看排名不看分数，因此不需要归一化两路的分数量纲——这是它比"加权求和"更省事、更稳的原因。

**先跑通纯向量（Phase 2），Phase 3 再加词法融合**，别一上来就上全。

### 4.5 权限：状态过滤是硬红线

只有 `status='published'` 的文章能进索引、能被检索。

- **索引时过滤**：`reindex_article()` 里文章非 published 就直接清空它的块（§7.2 的第一个分支）。
- **检索时也要过滤，而且在 SQL 里**：`search_dense`（§7.3）与 `_lexical_ids`（§7.5）都带 `JOIN article a … WHERE a.status = 'published'`。
  这不是"多查一次"的冗余——它是"库里那一行向量此刻属不属于公开语料"的唯一权威判断。
- 文章被改为非 published 时，`rag_reindex --prune` 必须**删除**它的块。

> 上一版这里必须提醒"内存索引可能还留着旧向量，所以结果返回前要按当前状态复核一遍"——因为索引是
> 进程内的快照，和库里的当前状态可能不一致。**换成 pgvector 后，这个不一致在结构上就不存在了**：
> 过滤条件和向量读的是同一张表、同一个事务快照。这条"硬红线"从"需要小心维护"变成了"把 WHERE 写对"。
>
> 不过 §7.5 的 `retrieve()` 里取块时那一次 `article__status='published'` **保留**：两层过滤都在 SQL，
> 成本可忽略，但任一层写错都不会泄漏。**草稿泄漏是不可逆事故，别为了省一次 JOIN 去掉。**

### 4.6 索引失效与 ANN 索引：两件事都不用做

**失效策略：这个问题不存在了。** 上一版整节讲的"内存索引多 worker 不同步 + `MAX(updated_at)` 版本号惰性刷新"在 pgvector 下**整段消失**：向量就在表里，检索读的是提交后的最新值，任何 worker 写完立刻全局可见。不需要 `invalidate()`、不需要版本探测、不需要给 `updated_at` 建索引。

**ANN 索引：现在别建，过万再建。** 建它不是单纯的"更快"，而是"更快但可能漏"：

```python
# 块数超过约 1 万之后再往 ArticleChunk.Meta.indexes 里加这一条。
# 好在 pgvector 提供了 Django 原生的 HnswIndex，不用写裸 SQL。
from pgvector.django import HnswIndex

indexes = [
    HnswIndex(
        name='idx_chunk_embedding_hnsw',
        fields=['embedding'],
        m=16,
        ef_construction=64,
        opclasses=['vector_cosine_ops'],   # 必须与检索用的算子（<=>）一致
    ),
]
```

| 块数 | 该不该建 ANN 索引 |
|---|---|
| < 1 万 | **不建。** 顺序扫描是精确的，几十毫秒以内；建索引白牺牲召回率 |
| 1 万 ~ 10 万 | 建 HNSW。`ivfflat` 建索引前表里得有数据（见下面的坑），HNSW 没这个要求 |
| > 10 万 | 建 HNSW，并把 `hnsw.ef_search` 调大（默认 40，越大越准越慢），同时开始考虑 rerank |

确认当前走的是什么计划：

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM article_chunk
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[...]'
LIMIT 20;
```

> **小表上看到 `Seq Scan` 是正常的，不是索引没建上**（2026-10-03 实测）：拿一张 3 行的临时表建好
> `hnsw (e vector_cosine_ops)` 之后，`EXPLAIN` 给出的计划仍然是 `Seq Scan on _probe` —— 规划器算下来
> 顺序扫描更便宜。索引确实建成了、也确实有效，只是这个规模轮不到它。**别因为看见 `Seq Scan`
> 就去反复重建索引**。真正该警惕的是相反的情形：数据已经过万，`EXPLAIN` 却还是 `Seq Scan`，
> 那才说明索引没被用上（多半是 `opclasses` 与检索算子不配套）。

> **`ivfflat` 的坑（所以推荐 HNSW）**：`ivfflat` 在**建索引时**要用表里已有的数据做 k-means 训练。
> 在空表或数据很少的表上建，会得到一个几乎没用的索引——之后插入的数据分不到合适的桶里，
> 召回率极低，而且**不报错**，你只会觉得"检索质量莫名其妙不行"。要用 `ivfflat` 就必须先灌满数据再建，
> 或者建完 `REINDEX`。HNSW 没有这个训练步骤，插一条索引一条，省心得多。
>
> **`opclasses` 必须和检索算子配套**：检索用 `<=>`（余弦距离）就写 `vector_cosine_ops`；
> 写成 `vector_l2_ops` 索引仍会建成功，但**查询不会用它**（静默退化成顺序扫描），
> 这在 `EXPLAIN` 里才能发现。

---

## 5. 数据模型

新建 Django 应用 `rag`（与 `chat_robot` 解耦：`rag` 负责知识库，`chat_robot` 只依赖它，反向不依赖）。

```python
# zdblog-master/rag/models.py
from django.db import models
from pgvector.django import VectorField

from article.models import Article
from tools.generate_nums import generate_uuid7


class ArticleChunk(models.Model):
    """文章切块 + 向量。派生数据，可从 article 表完整重建，不是权威数据源。"""

    id = models.CharField(primary_key=True, max_length=32, default=generate_uuid7, editable=False)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='chunks')

    ordinal = models.PositiveIntegerField(verbose_name='文章内顺序')
    heading = models.CharField(max_length=200, blank=True, verbose_name='标题路径')
    content = models.TextField(verbose_name='切块正文（含标题路径前缀）')
    char_count = models.PositiveIntegerField(default=0)
    content_hash = models.CharField(max_length=64, verbose_name='正文 sha256，用于增量判断')

    # pgvector 的 vector(1024) 列。Django 侧读写就是普通 list[float]：
    # VectorField.get_prep_value() 写入前转成字符串，from_db_value() 读取时解析回 list，
    # 两端都不需要注册 psycopg 适配器。（`dim` 字段也随之取消——维度写死在列类型里了。）
    embedding = VectorField(dimensions=1024, null=True, blank=True, verbose_name='向量')
    embedded_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True, verbose_name='最后重建时间（rag_status 的 stale 检查用）')

    class Meta:
        db_table = 'article_chunk'
        ordering = ['article_id', 'ordinal']
        constraints = [
            models.UniqueConstraint(fields=['article', 'ordinal'], name='uniq_chunk_article_ordinal'),
        ]
        indexes = [
            models.Index(fields=['article']),
            models.Index(fields=['content_hash']),
            # 上一版这里还有 updated_at（供内存索引做版本探测）；pgvector 下不需要了。
            # 块数过万时再按 §4.6 加 HnswIndex。
        ]
```

**`dimensions=1024` 是写死在列类型里的**，这是 `VectorField` 和 `BinaryField` 最大的行为差异：换一个维度不同的 embedding 模型时，不是"重建数据"就完事，而是**要先改列类型**：

```sql
ALTER TABLE article_chunk ALTER COLUMN embedding TYPE vector(1536);   -- 例：换成 1536 维模型
```

改完必须 `rag_reindex --force` 全量重算（不同模型的向量空间不可比，§11 坑 13）。
好处是：**维度写错会当场报错，而不是静默存进去**——比 `BinaryField` + 手工校验 `dim` 安全得多。
建议把 `1024` 与 `RAG_EMBED_DIM` 绑定成同一个常量，别在两处各写一遍。

**扩展的创建要手写进 `0001_initial`，而且必须排在 `CreateModel` 之前**——否则建表时列类型 `vector` 还不存在。Django 的 autodetector 生成不出这两条，得手工往迁移文件顶部插。好在 pgvector 和 Django 都提供了现成的操作，不用写裸 SQL：

```python
# zdblog-master/rag/migrations/0001_initial.py
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models
from pgvector.django import VectorExtension

import tools.generate_nums


class Migration(migrations.Migration):
    initial = True
    dependencies = [('article', '0001_initial')]

    operations = [
        # ① 扩展必须先建：CreateModel 里的 vector(1024) 列类型依赖它
        VectorExtension(),       # pgvector.django 提供，对 Django ≥ 6 有专门分支；底层就是 CreateExtension

        # ② pg_trgm 原生自带（实测 1.6 可用）。Django 6.0.5 里确认有 TrigramExtension
        #    （django/contrib/postgres/operations.py:104），不用自己写 RunSQL。
        TrigramExtension(),

        # ③ 建表。词法腿的 GIN 索引建在这里，因为此时扩展已经存在了。
        migrations.CreateModel(
            name='ArticleChunk',
            fields=[/* … 见上面的 models.py … */],
            options={
                'db_table': 'article_chunk',
                'indexes': [
                    models.Index(fields=['article']),
                    models.Index(fields=['content_hash']),
                    GinIndex(
                        name='idx_chunk_content_trgm',
                        fields=['content'],
                        opclasses=['gin_trgm_ops'],   # 三元组索引，LIKE '%…%' 与 % 算子才能用上
                    ),
                ],
            },
        ),
    ]
```

> **不用管事务**。`CreateExtension.database_forwards()` 就是直接一句
> `schema_editor.execute("CREATE EXTENSION IF NOT EXISTS …")`（已核对 Django 6.0.5 源码），
> 而 `CREATE EXTENSION` 在 PostgreSQL 里是事务性的，放在普通迁移事务中没有任何问题。
> **也不需要手工设 `atomic = False`**——网上有些帖子会这么建议，那是针对 `CREATE INDEX CONCURRENTLY` 的，
> 跟建扩展无关。

**`django.contrib.postgres` 要加进 `INSTALLED_APPS`**——本项目的 `INSTALLED_APPS`（[settings.py:38](../zdblog-master/config/settings.py#L38)）目前没有这一项。不加的话 `manage.py check` / `migrate` 会直接报：

```
postgres.E005: 'django.contrib.postgres' must be in INSTALLED_APPS in order to use GinIndex.
```

这不是"可选优化"：`GinIndex` 继承自 `PostgresIndex`，而 `PostgresIndex` 混入了 `CheckPostgresInstalledMixin`（`django/contrib/postgres/utils.py`），凡是 `Index.check()` 都会跑这个校验。§4.6 的 `HnswIndex` 同样受影响。加它**不需要装任何新包**，是 Django 自带的：

```python
INSTALLED_APPS = [
    ...
    'django.contrib.postgres',   # GinIndex / HnswIndex 都要求这一项，否则 postgres.E005
    ...
]
```

**不需要为 ANN 索引写迁移**——本规模不建（§4.6），要建的时候往 `Meta.indexes` 里加一条 `HnswIndex` 再 `makemigrations` 即可。

> **用 SQLite 跑测试**（`chat_robot/test_settings.py` 那套）时要小心，**失败方式很误导人**：
> 两条扩展操作会**静默跳过而不是报错**——`CreateExtension.database_forwards()` 开头有
> `if schema_editor.connection.vendor != "postgresql": return`（已核对 Django 6.0.5 源码）。
> 但 SQLite 上**没有 `vector` 类型、没有 `<=>` 算子、也没有 `gin_trgm_ops`**，
> 所以可能出现"迁移跑过了、测试也绿了，一上 PostgreSQL 才发现问题"的情况。
>
> **`rag` 的测试要么跑在 PostgreSQL 上，要么只测不碰数据库的纯函数**（切块 `split_article`、RRF 融合）。
> 非要在 SQLite 上跑整个 app，就给 `rag` 的迁移 `--fake`，并且测试里不要走 `retrieve()`。
> 好在 §7.5 的 `_lexical_ids` 本身写成了可降级（异常返回空列表），词法腿单独失败不会炸掉整条链路。

---

## 6. 分阶段落地

每个阶段都能独立验收，做完就能上线，不必等全部完成。

### Phase 0：给「博客助手」加约束（零成本，先做）

改 `chat_robot` 里「博客助手」persona 的 `system_prompt`，追加：

```
回答关于本站文章的问题时，只能依据工具返回的内容。工具返回「未找到」时，如实说明站内没有相关文章，
不要凭记忆编造文章标题、观点或链接。引用文章时给出可点击链接。
```

**当前是完全没有任何这类约束的**，模型问什么都敢答。这一条的收益大于后面所有工程投入——先加。

验收：问一个站内肯定没写过的话题（如"我写过 k8s operator 吗"），回答明确说没有，而不是编一篇。

### Phase 1：结构化检索工具（不碰向量）

把现有的 DRF `SearchFilter` 逻辑（[c_views.py:30](../zdblog-master/article/views/c_views.py#L30) 的 `search_fields = ['title', 'summary', 'content_md']`）包成一个 `@tool`，注册进 `build_agent`：

- 按关键词检索 `status='published'` 的文章，返回标题 + 摘要 + 正文命中片段 + `/article/<id>` 链接。
- 用 `icontains`/`LIKE` 即可。900 篇文章以内全表扫描无感；再大就加上 `pg_trgm` 的 GIN 索引（§5），`LIKE '%…%'` 也能走它。

验收：问"我写过哪篇讲 MySQL 索引的文章"，工具返回正确文章，模型回答带链接。

**做完 Phase 1 如果觉得够用，可以停在这里。** 后面的阶段解决的是语义召回和规模问题。

### Phase 2：向量索引 + 向量召回（本文核心）

1. 建 `rag` 应用与 `ArticleChunk` 模型（§5）。
2. 装 pgvector（§2.4）→ 建 `rag` 应用、写 §5 的模型与迁移 → `migrate` → `rag/embeddings.py`（§7.1）、`rag/indexer.py`（§7.2）、`rag/store.py`（§7.3）。
3. `manage.py rag_reindex` 管理命令（§7.4），跑一次全量索引。
4. `rag/retriever.py`（§7.5）把向量检索包成函数。
5. `chat_robot/tools.py` 新增 `search_blog` 工具（§7.6），`agent.py` 注册（§7.7）。

验收：
- `SELECT extname FROM pg_extension` 里有 `vector` 与 `pg_trgm`（§2.4 的验证语句先跑过）。
- `\d article_chunk` 显示 `embedding` 列类型是 `vector(1024)`。
- `manage.py rag_status` 显示 9 篇文章 → N 个块且全部 `embedded`，0 个 pending。
- 问"那篇讲前端性能优化的文章说了什么"，能召回正确文章。
- 问"站内有没有写过 Rust"，返回未找到，模型如实说明。
- 检索耗时 < 100 ms（不含 LLM）。

### Phase 3：词法融合 + 引用渲染 + 增量更新

1. 词法召回（`pg_trgm` 的 `%` 算子 + `similarity()` 排序）+ RRF 融合（§7.5）。
2. 前端引用链接渲染确认（白名单已允许 `<a>`，无需改前端）。
3. `Article` 的 `post_save` 信号触发该文章的增量重索引（§7.8）。
4. 可选：加 rerank（`bge-reranker-v2-m3` 或阿里 `gte-rerank`），先量化收益再加。

验收：
- 专有名词查询（如"pg_trgm"、"B+Tree"）能命中正确文章（词法腿的功劳）。
- 改一篇文章的正文 → 保存 → **立即**（不用跑命令、不用等、不用重启 worker）新内容可被检索到。
  这是 pgvector 相对内存索引最直观的一个改进：上一版受"多 worker 各自刷新"影响，只能承诺"几分钟内"。
- 把一篇文章改成 draft → 检索不到它，且它的块被删除。

### Phase 4：评估与调优

按 §9 建金标集，跑 `manage.py rag_eval`，记录 Recall@5 与 MRR 作为基线。之后每次改切块参数/embedding 模型/融合参数，都对比基线。

---

## 7. 代码骨架

> 以下均为可直接落地的骨架，不是伪代码。配置项见 §8。

### 7.1 `rag/embeddings.py`

```python
from functools import lru_cache

from django.conf import settings
from langchain_openai import OpenAIEmbeddings


@lru_cache(maxsize=1)
def get_embedder():
    return OpenAIEmbeddings(
        model=settings.RAG_EMBED_MODEL,
        base_url=settings.RAG_EMBED_BASE_URL,
        api_key=settings.RAG_EMBED_API_KEY,
        dimensions=settings.RAG_EMBED_DIM,
        # 非 OpenAI 官方端点必须关掉：否则它会先用 tiktoken 切分再请求，直接报错
        check_embedding_ctx_length=False,
        chunk_size=32,  # 单次请求的批大小，太大容易被网关拒绝
    )


def embed_documents(texts):
    """返回 list[list[float]]。"""
    return get_embedder().embed_documents(list(texts))


def embed_query(text):
    """返回 list[float]。转成 vector 是 pgvector 驱动/字段的事，不需要 numpy。"""
    return get_embedder().embed_query(text)
```

### 7.2 `rag/indexer.py` — 切块与增量入库

```python
import hashlib

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from article.models import Article
from .embeddings import embed_documents
from .models import ArticleChunk

HEADERS = [('#', 'h1'), ('##', 'h2'), ('###', 'h3'), ('####', 'h4')]


def _tail_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        separators=['\n\n', '\n', '。', '！', '？', '；', '，', ' ', ''],
    )


def split_article(article):
    """Markdown 标题感知切块，每块正文前置「《标题》 > 标题路径」。"""
    sections = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS, strip_headers=False,
    ).split_text(article.content_md or '')

    pieces = []
    for section in sections:
        path = ' > '.join(v for v in section.metadata.values() if v)
        prefix = f'《{article.title}》' + (f' > {path}' if path else '')
        for raw in _tail_splitter().split_text(section.page_content):
            body = raw.strip()
            if len(body) < settings.RAG_MIN_CHUNK_CHARS:
                continue  # 丢掉空块 / 只有标题的块
            content = f'{prefix}\n{body}'
            pieces.append({
                'heading': path,
                'content': content,
                'char_count': len(content),
                'content_hash': hashlib.sha256(content.encode('utf-8')).hexdigest(),
            })
    return pieces


def reindex_article(article, dry_run=False, force=False):
    """按内容 hash 增量更新单篇文章的块。文章非 published 时清空它的块。"""
    if article.status != Article.STATUS_PUBLISHED:
        deleted = article.chunks.count()
        if not dry_run:
            article.chunks.all().delete()
        return {'embedded': 0, 'reused': 0, 'deleted': deleted, 'total': 0}

    pieces = split_article(article)
    # 旧向量按内容 hash 复用：正文没变的块不重复调 embedding 接口。
    # VectorField 读出来就是 list[float]，直接拿来用。
    old = {c.content_hash: list(c.embedding) for c in article.chunks.all() if c.embedding}

    todo = [p for p in pieces if force or p['content_hash'] not in old]
    stats = {'embedded': len(todo), 'reused': len(pieces) - len(todo),
             'deleted': article.chunks.count(), 'total': len(pieces)}
    if dry_run:
        return stats

    vectors = dict(old)
    if todo:
        for piece, vector in zip(todo, embed_documents([p['content'] for p in todo])):
            vectors[piece['content_hash']] = vector   # list[float]，交给 VectorField 转换

    # 整篇删除 + 重建，而不是按 ordinal 逐块 update_or_create：
    # 新块插到文章中间时后面的 ordinal 会整体位移，按 ordinal 匹配会撞
    # (article, ordinal) 唯一约束，甚至把本该复用的块覆盖掉。
    # chunk.id 不被任何地方引用，重建的代价只是这张小表的写入。
    with transaction.atomic():
        article.chunks.all().delete()
        ArticleChunk.objects.bulk_create([
            ArticleChunk(
                article=article,
                ordinal=ordinal,
                heading=piece['heading'],
                content=piece['content'],
                char_count=piece['char_count'],
                content_hash=piece['content_hash'],
                embedding=vectors[piece['content_hash']],
                embedded_at=timezone.now(),
            )
            for ordinal, piece in enumerate(pieces)
        ])
    return stats
```

> **`bulk_create` 与 `updated_at`**：`bulk_create` 不触发 `save()`/`post_save` 信号，但它**会**对每个字段调用
> `field.pre_save(obj, add=True)`，所以 `auto_now=True` 依然生效，`updated_at` 会被刷新。
>
> 上一版这里依赖它做内存索引的版本探测，**现在检索完全不依赖它了**——留着只是为了 `rag_status`
> 判断"文章比索引新"（§7.8）。所以哪天改成 `bulk_update`（不走 `pre_save`）导致 `updated_at` 不刷新，
> 后果从"检索一直返回旧结果"降级成了"stale 检查不准"，不再是正确性问题。

### 7.3 `rag/store.py` — 向量检索（一条 SQL）

这一层刻意保持"薄"：**它是在 pgvector 和未来的 Qdrant 之间唯一需要替换的模块**（§13）。
`retriever.py` 只依赖 `search_dense()` 的签名，不关心底下是什么。

```python
"""向量召回。整个模块就是一条 SQL —— 没有进程内矩阵，没有失效逻辑，没有锁。"""

from django.db import connection


def _literal(vector):
    """pgvector 接受 '[1,2,3]' 这种字面量，配合 ::vector 强转不依赖驱动适配器。

    VectorField 在 ORM 写入时自己会做这个转换；这里走的是裸 cursor，所以要手工转。
    1024 维约 20 KB 文本，一次请求传两遍（SELECT 与 ORDER BY 各一次）也无所谓。
    """
    return '[' + ','.join(repr(float(x)) for x in vector) + ']'


def search_dense(query_vector, top_k=20, allow_articles=None):
    """返回 [(chunk_id, article_id, score), ...]，按相似度降序。

    score 是余弦相似度（= 1 - 余弦距离），越大越相似，与上一版 numpy 的语义保持一致。
    status 过滤直接写在 SQL 里 —— 不存在"索引里还留着 draft 文章向量"这种情况。
    """
    vec = _literal(query_vector)
    sql = [
        'SELECT c.id, c.article_id, 1 - (c.embedding <=> %s::vector) AS score',
        'FROM article_chunk c',
        'JOIN article a ON a.id = c.article_id',
        "WHERE c.embedding IS NOT NULL AND a.status = 'published'",
    ]
    params = [vec]

    if allow_articles is not None:
        sql.append('AND c.article_id = ANY(%s)')
        params.append(list(allow_articles))

    # <=> 是 pgvector 的余弦距离算子。ORDER BY 里必须再出现一次向量字面量，
    # 规划器才可能用上（将来建的）HNSW 索引 —— 用 CTE 包一层也行，直接写两遍最简单。
    sql.append('ORDER BY c.embedding <=> %s::vector LIMIT %s')
    params.extend([vec, top_k])

    with connection.cursor() as cursor:
        cursor.execute(' '.join(sql), params)
        return [(row[0], row[1], float(row[2])) for row in cursor.fetchall()]
```

**`<=>` 是余弦距离，不是相似度**：它返回 `1 - cos(θ)`，**越小越相似**，所以 `ORDER BY` 用升序（默认）。要展示给用户的 `score` 得翻过来（`1 - 距离`），否则"分数越高越相关"的直觉会反过来。

**三个距离算子别混用**：`<=>` 余弦距离、`<->` L2 距离、`<#>` 负内积。混用**不会报错**，只会给你一个"能跑但排序没道理"的结果——而且如果之后建了索引，`opclasses` 与算子不匹配时索引会静默不生效（§4.6）。

**想用 ORM 而不是裸 SQL**：`pgvector.django` 提供了 `CosineDistance`，可以写成
`ArticleChunk.objects.filter(article__status='published', embedding__isnull=False).order_by(CosineDistance('embedding', query_vector))[:top_k]`。
两种写法等价，SQL 版更容易看出"状态过滤在同一层"，ORM 版更符合项目其余部分的风格——**按团队习惯选一种，别两处都写**。

### 7.4 `rag/management/commands/rag_reindex.py`

```python
from django.core.management.base import BaseCommand

from article.models import Article
from rag.indexer import reindex_article


class Command(BaseCommand):
    help = '重建博客知识库索引（默认只处理新增/变更的块）'

    def add_arguments(self, parser):
        parser.add_argument('--article-id', help='只重建指定文章')
        parser.add_argument('--force', action='store_true', help='忽略 hash，全部重新 embedding')
        parser.add_argument('--dry-run', action='store_true', help='只统计，不写库')
        parser.add_argument('--prune', action='store_true', help='同时清理非 published 文章的块')

    def handle(self, *args, **options):
        articles = Article.objects.all()
        if options['article_id']:
            articles = articles.filter(pk=options['article_id'])
        elif not options['prune']:
            articles = articles.filter(status=Article.STATUS_PUBLISHED)

        total = {'embedded': 0, 'reused': 0, 'deleted': 0}
        for article in articles.iterator():
            stats = reindex_article(article, dry_run=options['dry_run'], force=options['force'])
            for key in total:
                total[key] += stats[key]
            if stats['embedded'] or stats['deleted']:
                self.stdout.write(f"{article.title}: {stats}")
        self.stdout.write(self.style.SUCCESS(f"完成 {total}"))
```

配套一个 `rag_status` 命令，输出：文章数、块数、已 embedding / 待 embedding 数、向量占用字节数、最后更新时间。**上线后它是你最常看的命令。**

### 7.5 `rag/retriever.py` — 混合检索

```python
from django.conf import settings
from django.db import connection

from .embeddings import embed_query
from .models import ArticleChunk
from .store import search_dense

RRF_K = 60


def _lexical_ids(query, limit=20):
    """pg_trgm 词法召回。失败时降级为空（只用向量腿）。

    用 % 算子做过滤（相似度超过 pg_trgm.similarity_threshold，默认 0.3，
    可在库里 SET 调整），再用 similarity() 排序，这样 §5 那个 GIN 索引才用得上。
    """
    try:
        with connection.cursor() as cursor:
            # 注意：Django 的 cursor 用 %s 做占位符，SQL 里字面的 % 要写成 %%。
            cursor.execute(
                'SELECT c.id FROM article_chunk c '
                'JOIN article a ON a.id = c.article_id '
                "WHERE a.status = 'published' AND c.content %% %s "
                'ORDER BY similarity(c.content, %s) DESC LIMIT %s',
                [query, query, limit],
            )
            return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []


def _rrf(rank_lists):
    scores = {}
    for ids in rank_lists:
        for rank, chunk_id in enumerate(ids):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    return sorted(scores.items(), key=lambda kv: -kv[1])


def retrieve(query, top_k=5, candidate_k=20):
    """返回 [{chunk_id, article_id, title, heading, snippet, url, score}, ...]"""
    dense = [(chunk_id, score) for chunk_id, _, score in search_dense(embed_query(query), candidate_k)]
    lexical = _lexical_ids(query, candidate_k)
    # 融合逻辑与上一版完全一致：RRF 只看排名，不看两路的分数量纲，
    # 所以换成 pg_trgm 的 similarity 分数不需要任何归一化调整。

    fused = _rrf([[c for c, _ in dense], lexical])[:top_k * 2]
    max_chars = settings.RAG_SNIPPET_CHARS

    chunks = {c.id: c for c in ArticleChunk.objects
              .select_related('article')
              .filter(id__in=[c for c, _ in fused], article__status='published')}

    results = []
    for chunk_id, score in fused:
        chunk = chunks.get(chunk_id)          # 复核：索引后被改成 draft 的会在这里被过滤掉
        if chunk is None:
            continue
        body = chunk.content
        if len(body) > max_chars:
            body = body[:max_chars] + '…'
        results.append({
            'chunk_id': chunk.id,
            'article_id': chunk.article_id,
            'title': chunk.article.title,
            'heading': chunk.heading,
            'snippet': body,
            'url': f'/article/{chunk.article_id}',
            'score': round(score, 6),
        })
        if len(results) >= top_k:
            break
    return results
```

### 7.6 `chat_robot/tools.py` — 新增 `search_blog`

```python
@tool
def search_blog(query: str) -> str:
    """当用户询问本站文章的内容、博主写过的观点、文章里出现过的技术细节时，使用此工具。

    与 search_func 的分工（务必分清）：
    - 站内文章、博客内容 → 用本工具
    - 实时信息、新闻、站外资料 → 用 search_func
    本工具返回「站内未找到」时，如实告知用户站内没有相关文章，**不要凭记忆编造文章标题、观点或链接**。

    输入：检索关键词或自然语言问题
    返回：相关文章片段（含《标题》、章节、正文片段、链接），最多 5 条
    """
    from rag.retriever import retrieve

    hits = retrieve(query, top_k=5)
    if not hits:
        return '站内未找到相关文章。'

    blocks = []
    for hit in hits:
        heading = f' > {hit["heading"]}' if hit['heading'] else ''
        blocks.append(f'《{hit["title"]}》{heading}\n{hit["snippet"]}\n链接：{hit["url"]}')

    text = '\n\n'.join(blocks)
    # 硬截断：这个返回值会被完整序列化进 ChatConversation.agent_messages(JSONField)，
    # 且占后续每一轮的上下文预算
    limit = 1500
    return text if len(text) <= limit else text[:limit] + '\n（内容过长已截断）'
```

### 7.7 `chat_robot/agent.py` — 按角色配置工具

现状是**所有角色共用同一套工具**（`ChatPersona` 没有工具字段），语义分析工具根本不在 `build_agent` 里。要按角色区分，先给模型加字段：

```python
# chat_robot/models.py — ChatPersona 新增
tools = models.JSONField(default=list, blank=True, verbose_name='可用工具名列表')

# chat_robot/models.py — ChatConversation 新增（沿用现有快照模式）
persona_tools = models.JSONField(default=list, blank=True, verbose_name='人设工具快照')
```

> **为什么要快照**：`ChatConversation.persona` 是 `SET_NULL`，人设删除后历史会话还要能复现当时的行为。现有代码已经把 `system_prompt`/`greeting` 快照下来了，工具列表属于同一类「agent 配置」，应当一起快照。`ChatStreamView` 创建会话时写入，`build_agent` 时读取。

```python
# chat_robot/agent.py
from .tools import get_weather, search_func, search_blog, handle_tool_errors, analyze_sentiment

TOOL_REGISTRY = {
    'get_weather': get_weather,
    'search_func': search_func,   # 联网搜索
    'search_blog': search_blog,   # 站内知识库
    'analyze_sentiment': analyze_sentiment,
}
DEFAULT_TOOLS = ['get_weather', 'search_func']


def build_agent(system_prompt, tool_names=None):
    names = tool_names or DEFAULT_TOOLS
    tools = [TOOL_REGISTRY[n] for n in names if n in TOOL_REGISTRY]
    return create_agent(
        model=get_llm_model(),
        system_prompt=system_prompt,
        tools=tools,
        middleware=[
            handle_tool_errors,
            SummarizationMiddleware(
                model=get_llm_model(), trigger=('tokens', 10000), keep=('messages', 20),
            ),
        ],
    )
```

「博客助手」的 `tools` 配 `['search_blog', 'search_func', 'get_weather']`，「明日香」保持默认（不给她站内检索——她的回答不该引用文章）。

### 7.8 增量更新：`Article.post_save` 信号

```python
# rag/signals.py
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from article.models import Article

# 这些字段变动不需要重建索引
IGNORED_FIELDS = {'view_count', 'like_count', 'comment_count', 'updated_at'}


@receiver(post_save, sender=Article)
def article_saved(sender, instance, created, update_fields, **kwargs):
    if update_fields is not None and IGNORED_FIELDS.issuperset(update_fields):
        return
    transaction.on_commit(lambda: _enqueue(instance.pk))


def _enqueue(article_id):
    from rag.indexer import reindex_article
    from article.models import Article as A
    article = A.objects.filter(pk=article_id).first()
    if article is not None:
        reindex_article(article)
```

**注意两点**（都是本项目的具体事实）：

1. 文章详情页用 `Article.objects.filter(pk=...).update(view_count=F('view_count') + 1)` 自增浏览（[c_views.py:66](../zdblog-master/article/views/c_views.py#L66)）。**queryset 的 `.update()` 不触发 `post_save`**，所以不会因为有人看文章就疯狂重建索引——这是好事，但也意味着**批量/queryset 更新不会自动同步索引**，所以需要一个兜底：`rag_status` 里加一个 stale 检查（比对 `article.updated_at` 与块的最大 `embedded_at`），或者挂个每日定时任务跑 `rag_reindex`。
2. 没有 Celery。同步 embedding 会让后台保存文章慢 1-3 秒。文章量小时可接受；要异步就得先引入任务队列——**先同步，别提前引框架**。

### 7.9 `rag/management/commands/rag_eval.py` — 评估

```python
import json

from django.core.management.base import BaseCommand

from rag.retriever import retrieve


class Command(BaseCommand):
    help = '跑金标集评估检索质量（Recall@k / MRR / 负例正确率）'

    def add_arguments(self, parser):
        parser.add_argument('--gold', default='docs/rag_gold.jsonl')
        parser.add_argument('--k', type=int, default=5)

    def handle(self, *args, **options):
        k = options['k']
        with open(options['gold'], encoding='utf-8') as fh:
            cases = [json.loads(line) for line in fh if line.strip()]

        pos_hit = pos_total = 0
        mrr = 0.0
        neg_total = neg_ok = 0

        for case in cases:
            got = [r['article_id'] for r in retrieve(case['q'], top_k=k)]
            expect = case.get('expect') or []

            if not expect:                      # 负例：一条都不该召回
                neg_total += 1
                neg_ok += 1 if not got else 0
                self.stdout.write(f"  [负例] {case['q']} → {'通过' if not got else f'不该召回 {got}'}")
                continue

            rank = next((i + 1 for i, aid in enumerate(got) if aid in expect), None)
            pos_total += 1
            if rank:
                pos_hit += 1
                mrr += 1.0 / rank
            self.stdout.write(f"  {case['q']} → {rank or '未命中'}")

        pos_total = max(pos_total, 1)
        self.stdout.write(self.style.SUCCESS(
            f'Recall@{k}: {pos_hit / pos_total:.2f} | MRR: {mrr / pos_total:.2f} | '
            f'负例正确率: {neg_ok}/{neg_total}'
        ))
```

> 这个脚本量的是**检索质量**，不是**回答质量**。回答质量（有没有如实说"没找到"）要人工抽查，或者再接一个用 LLM 打分的 judge——先人工，别一上来就搭 judge。

---

## 8. 配置

```python
# zdblog-master/config/settings.py
# ── RAG（博客知识库）──
RAG_ENABLED = os.getenv('RAG_ENABLED', 'true').lower() == 'true'
RAG_EMBED_BASE_URL = os.getenv('RAG_EMBED_BASE_URL', '')       # 如 https://api.siliconflow.cn/v1
RAG_EMBED_API_KEY = os.getenv('RAG_EMBED_API_KEY', '')
RAG_EMBED_MODEL = os.getenv('RAG_EMBED_MODEL', 'BAAI/bge-m3')
RAG_EMBED_DIM = int(os.getenv('RAG_EMBED_DIM', '1024'))

RAG_CHUNK_SIZE = int(os.getenv('RAG_CHUNK_SIZE', '400'))       # 单块目标字数
RAG_CHUNK_OVERLAP = int(os.getenv('RAG_CHUNK_OVERLAP', '60'))
RAG_MIN_CHUNK_CHARS = int(os.getenv('RAG_MIN_CHUNK_CHARS', '30'))
RAG_TOP_K = int(os.getenv('RAG_TOP_K', '5'))
RAG_CANDIDATE_K = int(os.getenv('RAG_CANDIDATE_K', '20'))
RAG_SNIPPET_CHARS = int(os.getenv('RAG_SNIPPET_CHARS', '300'))
```

`.env` 里加 `RAG_EMBED_BASE_URL` 与 `RAG_EMBED_API_KEY`。**key 只进 `.env`**（`.gitignore` 已忽略），不要硬编码、不要写进本文档、不要在日志里打印。

> **`RAG_EMBED_DIM` 必须与 `ArticleChunk.embedding` 的 `VectorField(dimensions=…)` 一致**（§5）。
> 两处不一致时数据库会拒绝写入（这是好事，比静默存错维度强），但报错信息是
> `expected 1024 dimensions, not 1536` 这种——看到要能立刻想到是这里，而不是去怀疑 embedding 服务。

`requirements.txt` 显式补上（**2026-10-03 已加**）：

```
pgvector==0.5.0
langchain-text-splitters==1.1.2
```

> **版本号写死，别改成 `>=`**：本项目 `requirements.txt` 里所有包都是 `==` 锁定的（可复现构建），
> 新增依赖跟着这个约定走。版本号取自本机实测装好的版本。
>
> `langchain-text-splitters` 之前是通过 `langchain` 传递装上的。**传递依赖不能当作自己的依赖**——上游哪天换实现，你的代码就断。
> `pgvector` 是本次新增的，纯 Python 无编译。
> `numpy` **不再列入**（§2.1）：向量运算已全部下推给数据库，它不再是核心路径的依赖。
>
> **`pgvector` 这个 pip 包只是 Python 侧的封装**（`VectorField` / `VectorExtension` / `HnswIndex`）——它**不含数据库扩展**。
> 只 `pip install` 而没执行 `CREATE EXTENSION vector`，`migrate` 会在建表时报 `类型 "vector" 不存在`。
> **两边都要做，缺一不可**（§2.4）。

---

## 9. 检索质量评估

没有 eval 的 RAG 调不动——你会一直在"感觉变好了"和"感觉变差了"之间打转。

金标集放 `docs/rag_gold.jsonl`，一行一题：

```jsonl
{"q": "Django 里怎么写 REST API", "expect": ["bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb02"]}
{"q": "Python 的 async/await 是怎么演进过来的", "expect": ["bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb01"]}
{"q": "Vue3 的 setup 语法糖怎么用", "expect": ["bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb03"]}
{"q": "MySQL 索引为什么选 B+Tree", "expect": ["bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb04"]}
{"q": "宏任务和微任务的区别", "expect": ["bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb05"]}
{"q": "今年有什么值得看的书", "expect": ["bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb07"]}
{"q": "怎么从零搭一个自己的博客", "expect": ["bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb08"]}
{"q": "什么是原生多模态", "expect": ["019e3982e9e77261933f14e0fc345855"]}
{"q": "首屏加载太慢怎么优化", "expect": ["bbbbbbbbbbbb4bbb8bbbbbbbbbbbbb10"]}
{"q": "Redis 缓存穿透怎么解决", "expect": []}
{"q": "k8s 的 operator 怎么写", "expect": []}
{"q": "我写过 Rust 的什么内容", "expect": []}
```

**最后三条负例是最重要的部分**。RAG 最典型的失败模式不是"召不回"，而是"召不回还硬答"——模型看到工具返回空，仍然顺着自己的训练知识编一篇。负例的验收标准是：模型明确说站内没有相关文章。

打分脚本见 §7.9（`manage.py rag_eval`），输出：

| 指标 | 含义 | 目标 |
|---|---|---|
| Recall@5 | 正确文章出现在前 5 条的比例 | ≥ 0.85 |
| MRR | 第一个正确结果的排名倒数均值 | ≥ 0.7 |
| 负例正确率 | 负例被正确判空的比例 | 100% |

调参顺序（每次只动一个，动完跑 eval）：
1. 切块大小 / 重叠（`RAG_CHUNK_SIZE` 400 → 300 / 600）
2. 是否加词法融合（Phase 3 前后对比）
3. `RAG_CANDIDATE_K`（20 → 40）
4. 换 embedding 模型（**必须全量重建**）
5. 加 rerank

---

## 10. 运维

| 场景 | 操作 |
|---|---|
| 首次建索引 | `python manage.py rag_reindex` |
| 单篇文章改完手动重建 | `python manage.py rag_reindex --article-id <id>` |
| 换了 embedding 模型 | `python manage.py rag_reindex --force`（必须全量，向量空间不可比） |
| 文章改回 draft | `python manage.py rag_reindex --prune` |
| 看当前状态 | `python manage.py rag_status` |
| 跑评估 | `python manage.py rag_eval --gold docs/rag_gold.jsonl --k 5` |

- **`article_chunk` 是可重建的派生数据**：出问题直接 `TRUNCATE` 再 `rag_reindex`，不必备份、不必惊慌。前提是 `article.content_md` 完好——所以**备份的重点是 `article` 表**。
- **磁盘占用**：向量按 `块数 × 1024 × 4` 字节算，2000 块 = 8 MB。整表连同正文，1000 篇文章也就几十 MB。
- **重建不要用「先 TRUNCATE 再逐条插」**：中间态会让在线检索返回空结果。按文章粒度事务替换（§7.2 的写法），或者重建到临时表再原子切换。
- **部署**：新增 `rag` 应用要在部署流程里加 `manage.py migrate`。**`rag` 的 `0001_initial` 会执行 `CREATE EXTENSION vector` / `pg_trgm`，需要超级用户权限**——生产上如果应用连的是普通角色，把建扩展提到部署前的 DBA 步骤（一次性），迁移里只留 `CreateModel` 与索引（§5）。
- **生产装 pgvector（Linux，比 Windows 简单得多）**：
  ```bash
  apt install postgresql-17-pgvector      # PGDG 源；大版本号要对齐你的 PG
  ```
  Windows 那堆折腾（§2.4）只发生在开发机，别把它当成部署成本。**开发机已于 2026-10-03 装好**，
  生产环境仍要走一次这条命令 + 每个库各 `CREATE EXTENSION` 一遍。
- **上线前必查**：`SELECT extname FROM pg_extension;` 必须有 `vector`。缺了它，检索会在第一次调用时报
  `operator does not exist: vector <=> vector`——这个报错出现在运行时而不是启动时，容易漏到线上。

---

## 11. 本项目特有的坑

1. **Windows 上得自己编译 pgvector，官方不提供预编译包**（开发机 2026-10-03 已装好，见 §2.4；换机器要重做）。两个容易记反的点：一是 `pip install pgvector` **只装 Python 侧**，装完数据库里照样没有 `vector` 类型，两边缺一不可；二是 `nmake /F Makefile.win install` 在本机**会无声失败**，改用纯拷贝的 `install-manual.bat`。
2. **`CREATE EXTENSION vector` 需要超级用户**。本机连的是超管 `root`，随便建；生产上要是应用账号不是超管，`migrate` 会断在这一步（§5、§10）。另注意扩展是**按库**安装的，同一个集群里新建一个库要重新建一次。
3. **词法腿用 `pg_trgm`，它是原生自带的**（实测 1.6 可用）。别去找 MySQL 那种 ngram 分词器——PostgreSQL **没有内置的中文分词**，`pg_trgm` 是按字符切三元组，中文子串检索够用。真需要词级中文切分得上 `zhparser` / `pgroonga`，那是另一个量级的安装成本（同样要编译），本项目不需要。
4. **索引 `content_md` 而不是 `content_html`**。HTML 里全是标签和高亮 span，进 embedding 就是噪声。
5. **只索引 `status='published'`**，草稿和私密文章进索引等同于泄漏。检索时还要按当前状态**复核一遍**（§7.5 的 `article__status='published'`）。
6. **工具返回值必须有长度上限**。`search_blog` 的返回值会经 LangGraph 的 tool message 一路序列化进 `ChatConversation.agent_messages`（JSONField），还会占后续每一轮的上下文预算。整篇文章塞进去 = 同时撑爆数据库字段和 token 预算。上限 1500 字、最多 5 条。
7. **工具 docstring 就是给模型看的 prompt**。现在已有 `search_func`（联网搜索），新工具的 docstring 必须写清"站内用 `search_blog`、站外用 `search_func`"，否则模型会分不清——出现"你博客里没写过"其实它去搜了互联网这种诡异行为。
8. **`ChatPersona` 没有工具字段，所有角色共用同一套工具**（`build_agent` 写死的）。要么给所有角色都加，要么按 §7.7 加字段 + 快照。这是个需要先做的设计决定。
9. **人设是快照的、`persona` 外键是 `SET_NULL`**。工具列表属于 agent 配置，要跟 `system_prompt` 一起快照到会话上，否则删掉人设后历史会话会突然换行为。
10. **`SummarizationMiddleware` 不是知识库**。它压缩的是对话历史（10k token 触发、保留 20 条），跟文章检索无关。别指望它能"记住"文章内容。
11. **文章详情页的浏览计数走 queryset `.update()`，不触发 `post_save`**——这是好事（不会看一次文章就重建一次索引），但也意味着 queryset 更新不会同步索引，需要 stale 兜底检查（§7.8）。
12. **前端 Markdown 白名单允许 `<a>`，但会把相对链接解析成站点的绝对 URL**（`chatMarkdown.js`），所以引用直接写 `[《标题》](/article/<id>)` 就能点。**但不允许 `<img>`**——别让模型输出图片 Markdown，会被降级成纯文本。
13. **换 embedding 模型 = 必须全量重建**。不同模型的向量空间不可比，混着用会让检索结果变成随机。
    维度变了还要先 `ALTER COLUMN ... TYPE vector(N)`（§5）。**维度没变、只换了模型的情况，数据库查不出来**——
    上一版靠 `store.py` 里 `vector.size != dim` 的校验也只能挡住维度不同的，同维度不同模型一样挡不住。
    所以换模型的标准动作永远是：改列类型（如需要）+ `rag_reindex --force`，别省。
14. **`<=>` 是距离不是相似度**（越小越相似），`ORDER BY` 用升序、展示的 `score` 要 `1 - 距离`（§7.3）。
    它和 `<->`（L2）、`<#>`（负内积）混用**不会报错**，只会给你一个"能跑但排序没道理"的结果。
15. **Django 的 raw cursor 里 `%` 要写成 `%%`**（§7.5 的 `content %% %s`）。psycopg 会先拿 `%` 做占位符解析，
    不转义就报 `unsupported format character`。
16. **多 worker 不同步的问题在这个方案下不存在了**。上一版必须处理它（内存索引各持一份，`runserver` reload 都能让索引失效），
    所以有 `invalidate()`、版本号、`MAX(updated_at)` 一整套机制。现在向量就在表里，任何 worker 写完立刻全局可见，
    **那套机制整段删掉**——这是换 pgvector 拿到的最实在的一个好处。

---

## 12. 验收清单

**前置（§2.4 已完成，2026-10-03 三条全部实测通过）**

- [x] `SELECT extname, extversion FROM pg_extension;` 里有 `vector 0.8.7` 与 `pg_trgm 1.6`
- [x] `SELECT '[1,2,3]'::vector <=> '[3,2,1]'::vector;` 返回 `0.2857142857142857`
      （**注意是余弦距离**；`2.8284271247461903` 是 `<->` 的 L2 距离，两个数别记混）
- [x] `python -c "import importlib.metadata as m; print(m.version('pgvector'))"` 输出 `0.5.0`
      （**别用 `pgvector.__version__`**，这个包没有该属性；且要在**非 `data/pgvector-build/` 的目录**下执行，
      否则会导入到那份克隆的源码目录，得到一个假的成功）

**功能**

- [ ] Phase 0：问站内没写过的话题，模型明确说"没写过"而不是编造
- [ ] Phase 1：关键词检索能命中正确文章，回答带可点击链接
- [ ] Phase 2：`\d article_chunk` 显示 `embedding` 列是 `vector(1024)`
- [ ] Phase 2：`rag_status` 显示 9 篇文章全部索引完成、0 pending
- [ ] Phase 2：语义提问（不含文章原词）能召回正确文章
- [ ] Phase 2：`status='private'` 的那篇文章**任何查询都检索不到**
- [ ] Phase 2：检索耗时 < 100 ms，且 `EXPLAIN ANALYZE` 确认走的是顺序扫描（本规模**不该**有 ANN 索引）
- [ ] Phase 3：改一篇文章正文 → 保存 → **立即**可检索到新内容（不用跑命令、不用重启 worker）
- [ ] Phase 3：把文章改成 draft → 检索不到，且块被删除
- [ ] Phase 3：专有名词查询能命中（词法腿生效）
- [ ] Phase 4：`rag_eval` 跑出基线，Recall@5 ≥ 0.85，负例正确率 100%
- [ ] 全流程：单轮对话的 tool message 序列化进 `agent_messages` 后，单条不超过 ~2 KB

---

## 13. 未来演进

- **Rerank**：chunk 数上千、Noise 明显时，加 `bge-reranker-v2-m3` 或阿里 `gte-rerank` 对 top 20 重排。先用 eval 量化收益再加，别凭感觉。
- **查询改写**：多查询扩展（Multi-Query）、HyDE。对短问句提升明显，对已经很好的中文语义检索收益有限。
- **建 ANN 索引**：chunk 数过万后按 §4.6 加 `HnswIndex`（纯 DDL + 一行 `Meta.indexes`，**不需要改任何代码逻辑**）。这一步比上一版方案容易得多——内存索引时代"过万"意味着要开始考虑换向量库。
- **换向量库**：chunk 数到百万级、或需要复杂的 payload filter 时，才轮到 Qdrant（单二进制、filter 好用）。
  `rag/store.py` 是唯一要换的模块（§7.3 刻意做成了薄封装），`retriever.py` 的接口不用变。
- **索引评论/标签页**：如果想让助手回答"读者怎么说"，把 Comment 纳入索引（注意：评论是用户生成内容，注入风险更高，需要额外防护）。
- **多模态**：文章封面与正文配图纳入检索。前端白名单目前不允许 `<img>`，需要同步调整。
