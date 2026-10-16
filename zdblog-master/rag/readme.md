# RAG 运行与维护

## 当前实现

用户已有的 `BAAI/bge-small-zh-v1.5`、512 维，本地 CPU 推理；使用 PostgreSQL `vector(512)` 精确余弦召回，与 `pg_trgm` 词法候选做 RRF 融合，不维护进程内向量矩阵、不建 ANN。只读取公开文章；草稿和私密文章不能被检索。

后端通过 `.env` 配置使用已有 `chat_with_doctor` Python 环境的离线常驻 worker，避免向 Django 环境重复安装 Torch。首次载入有冷启动成本，后续复用模型。`local_files_only=True`、`HF_HUB_OFFLINE=1` 和 `TRANSFORMERS_OFFLINE=1` 禁止下载模型；正文不发送到在线 embedding 服务。DeepSeek 仍接收聊天上下文与被检索到的有限文章片段，这一点沿用现有 Agent 架构。

后台 `/chats` 人物表单增加工具复选框：站内 RAG、联网搜索、天气、明日香情感分析。空工具列表表示全部关闭。新会话保存工具快照；新增迁移为“博客助手”及已有同名聊天启用 `search_blog`，追加工具引用与无命中约束，其他人物保留原工具配置。

同日新增结构化文章工具 `list_articles`、`count_articles`、`get_article`：最新发布/最近修改、数量及按 ID 阅读不走语义检索。迁移 `chat_robot.0007` 为已启用 search_blog 的角色和会话补齐这些工具，并删除 0006 引入的“所有本站问题先调用 search_blog”旧规则。Graph 动态注入任务选择规则；后台可分别开启各工具。日期范围默认按 Asia/Shanghai，列表默认最新 5 篇，详情支持正文分页，均只读取公开文章。详细实现和本次验证见 [Agent 说明](../chat_robot/readme.md)。

## 模块职责

| 模块 | 实现 |
| --- | --- |
| `models.py` | `ArticleChunk`：正文块、源版本、模型指纹、向量；`ArticleIndexState`：索引状态、版本与失败类型 |
| `indexer.py` | 标题感知递归切分、短段保留、内容 hash 复用；网络计算后锁文章并复核版本；每篇文章原子替换 |
| `embeddings.py` | 本地/API 两种适配、512 维非零有限向量校验、响应数量校验、模型指纹、query instruction |
| `local_embeddings.py` | 缓存直接推理实例或常驻子进程；请求串行化、UTF-8 JSON 管道、超时回收、退出清理 |
| `embedding_worker.py` | 独立环境中仅加载本地权重，归一化 embedding；不执行模型提供的自定义代码 |
| `store.py` | pgvector 余弦与模型指纹过滤；`word_similarity`、子串/术语匹配、事务局部阈值和 savepoint |
| `retriever.py` | 相关性门槛、RRF、公开状态与源 hash 复核、按文章去重、命中位置片段、实时文章关键词降级 |
| `signals.py` | 文章提交后同步更新索引，忽略计数变动；失败不影响已提交的文章保存，记录通用错误类型 |
| `evaluation.py` | 正确区分 Recall@k 与 HitRate@k，计算 MRR 和负例正确率 |

信号不监听 `QuerySet.update()`，但检索会对候选源 hash 复核，避免返回旧正文；实时关键词降级可以返回当前正文。批量更新后请运行 `rag_reindex` 恢复语义向量。文章删除由外键级联清理。标签/分类不作为索引正文，当前仅索引标题、Markdown 正文，summary 参与源版本和关键词兜底。

## 本机配置

本次已向忽略的 `.env` 添加以下有效配置（原有注释配置保留）：

```dotenv
RAG_ENABLED=true
RAG_EMBED_PROVIDER=local
RAG_EMBED_MODEL=BAAI/bge-small-zh-v1.5
RAG_EMBED_DIM=512
RAG_LOCAL_MODEL_PATH=../models/bge-small-zh-v1.5
RAG_LOCAL_DEVICE=cpu
RAG_LOCAL_PYTHON=D:/CondaEnvs/chat_with_doctor/python.exe
```

模型文件存放在仓库根目录 `models/bge-small-zh-v1.5`。`.env` 中的相对路径以 `zdblog-master` 后端目录为基准解析，因此不依赖启动命令所在的当前目录。如果在后端环境安装本地推理依赖，可以留空 `RAG_LOCAL_PYTHON`，在 Django worker 内缓存模型。当前复用环境实测依赖为 sentence-transformers 5.4.1、transformers 5.8.0、torch 2.11.0；部署时要单独准备相容的本地推理环境及模型文件。

兼容用户原有配置名 `BGE_MODEL_PATH`、`BGE_EMBEDDING_MODEL`、`EMBEDDING_DEVICE`，但注释行不会被 dotenv 读取。`RAG_*` 优先。`HF_HOME` 不代替明确的模型 snapshot 目录。

可选在线兼容接口：设置 `RAG_EMBED_PROVIDER=openai`、`RAG_EMBED_BASE_URL`、`RAG_EMBED_API_KEY`、`RAG_EMBED_MODEL`。模型必须返回 512 维。默认不传 `dimensions`，只有端点明确支持时才设置 `RAG_EMBED_SEND_DIMENSIONS=true`。换 1024 维模型需要 schema 迁移，不能只改 env。

配置 defaults 在 `rag/config.py`，由 `config/settings.py` 在读取 `.env` 后导入。默认 chunk 400 字，overlap 60，top-k 5，候选 20，片段 300 字，工具返回总预算 1,500 字。相关性阈值 `RAG_MIN_DENSE_SCORE=0.56`、`RAG_MIN_LEXICAL_SCORE=0.45` 已用当前本地模型和金标校准；换语料或模型需重新评估，RRF 分数不能充当概率或置信度。

## 操作命令

在后端目录、现有 `zblog-master` 环境中运行：

```powershell
python manage.py migrate
python manage.py rag_reindex --prune
python manage.py rag_status
python manage.py rag_eval
python manage.py rag_reindex --article-id <id>
python manage.py rag_reindex --force
python manage.py rag_reindex --dry-run
```

金标集为仓库根目录 `docs/rag_gold.jsonl`，默认路径不依赖当前 shell 目录。输出按文章去重，不让一篇文章的多个 chunk 占满评估排名。负例无命中仅表示本次检索没有证据，不代表全站永远没有此话题。

本次迁移新增 `article_chunk`、`article_rag_state` 与人物工具字段，不修改文章正文。迁移中预先建立 vector/pg_trgm 扩展；生产账号无权限时由 DBA 预先建扩展。换同维度 embedding 模型后旧模型指纹不会参与向量检索，需 `rag_reindex --force` 重建；维度变更需先清空旧派生向量，再修改固定 schema 常量及 Django 迁移。

## 验证与限制

```powershell
python manage.py test rag chat_robot --settings=rag.test_settings --noinput
python manage.py makemigrations --check --dry-run
```

测试使用独立的 `test_zdblog_rag` PostgreSQL 库，真实创建扩展和 `vector(512)` 列。embedding 在测试中替换为确定向量，不调用 DeepSeek；原聊天迁移测试继续使用独立 SQLite 连接。不要把 SQLite 测试结果当作 pgvector 集成验证。

2026-10-03 本机实测：30 项 `rag + chat_robot` 测试通过，后台 Vue 生产构建通过，Django 系统检查与迁移一致性检查通过。首次索引覆盖 9 篇公开文章、27 个正文块及 27 个 512 维向量，私密文章未入库。当前 13 条金标（10 正例、3 负例）的 Recall@5、HitRate@5、MRR、负例正确率均为 1.0。原 Rust 负例因书单正文含 Rust 教程已纠正，并增加 WebRTC ICE 负例。

这些数据同时用于阈值校准，属于小样本回归验证，不是独立测试集；不代表所有未知话题的准确率，也没有衡量返回列表中其余文章的 precision。此轮未调用在线 DeepSeek 验证最终回答质量，已验证真实本地 embedding、PostgreSQL 检索、引用格式及 Agent 工具循环。

同步索引让文章保存有额外延迟。本地 worker 在每个后端进程中各持一份模型；需按内存和并发规划 worker 数。首次加载可能数秒，已有模型后查询仍包含 CPU 推理时间，不能保证端到端检索恒定小于 100ms。启动环境更改后重启后端。

本机单次新进程 embedding 冷启动约 17 秒；完成索引、模型已驻留后，两次完整检索约 41–42ms（包含 embedding、SQL 和正文复核）。这只是当前小语料的观测值，不包含 DeepSeek 生成或聊天网络延迟。

工具结果通过完整链接分配字符预算，不在 URL 中间截断；1,500 个中文字符可能超过 4.5KB，JSON 和 Markdown 还有额外开销。展示历史中的旧引用/工具消息不会因文章后来设为私密而自动删除，新检索已按当前公开状态过滤。

长代码围栏可被递归切开，rerank、异步任务队列和检索 API 页面尚未加入。当前实现支持自然语言/术语混合检索，不保证未知话题 100% 判空；实际指标须以本站金标和模型实测结果为准。后台改工具配置默认只影响新会话；本次迁移对已有“博客助手”聊天做了一次明确升级。
