# RAG 运行与维护

## 当前实现

当前 Docker 部署使用阿里云百炼 `qwen3.7-text-embedding-flash` 在线生成 1024 维向量；使用 PostgreSQL `vector(1024)` 精确余弦召回，与 `pg_trgm` 词法候选做 RRF 融合，不维护进程内向量矩阵、不建 ANN。只读取公开文章；草稿和私密文章不能被检索。

文章分块内容会发送到嵌入服务生成向量，聊天查询也会发送给该服务；DeepSeek 仍接收聊天上下文与被检索到的有限文章片段，这一点沿用现有 Agent 架构。在线嵌入接口使用 OpenAI 兼容格式；模型切换和维度变更后必须重建公开文章索引。

后台 `/chats` 人物表单增加工具复选框：站内 RAG、联网搜索、天气、明日香情感分析。空工具列表表示全部关闭。新会话保存工具快照；新增迁移为“博客助手”及已有同名聊天启用 `search_blog`，追加工具引用与无命中约束，其他人物保留原工具配置。

同日新增结构化文章工具 `list_articles`、`count_articles`、`get_article`：最新发布/最近修改、数量及按 ID 阅读不走语义检索。迁移 `chat_robot.0007` 为已启用 search_blog 的角色和会话补齐这些工具，并删除 0006 引入的“所有本站问题先调用 search_blog”旧规则。Graph 动态注入任务选择规则；后台可分别开启各工具。日期范围默认按 Asia/Shanghai，列表默认最新 5 篇，详情支持正文分页，均只读取公开文章。详细实现和本次验证见 [Agent 说明](../chat_robot/readme.md)。

## 模块职责

| 模块 | 实现 |
| --- | --- |
| `models.py` | `ArticleChunk`：正文块、源版本、模型指纹、向量；`ArticleIndexState`：索引状态、版本与失败类型 |
| `indexer.py` | 标题感知递归切分、短段保留、内容 hash 复用；网络计算后锁文章并复核版本；每篇文章原子替换 |
| `embeddings.py` | 在线 OpenAI 兼容 API 适配、1024 维非零有限向量校验、响应数量校验、模型指纹 |
| `local_embeddings.py` | 可选本地模型 worker；模型输出维度必须匹配当前 `vector(1024)` schema |
| `embedding_worker.py` | 可选隔离环境加载本地权重；不执行模型提供的自定义代码 |
| `store.py` | pgvector 余弦与模型指纹过滤；`word_similarity`、子串/术语匹配、事务局部阈值和 savepoint |
| `retriever.py` | 相关性门槛、RRF、公开状态与源 hash 复核、按文章去重、命中位置片段、实时文章关键词降级 |
| `signals.py` | 文章提交后同步更新索引，忽略计数变动；失败不影响已提交的文章保存，记录通用错误类型 |
| `evaluation.py` | 正确区分 Recall@k 与 HitRate@k，计算 MRR 和负例正确率 |

信号不监听 `QuerySet.update()`，但检索会对候选源 hash 复核，避免返回旧正文；实时关键词降级可以返回当前正文。批量更新后请运行 `rag_reindex` 恢复语义向量。文章删除由外键级联清理。标签/分类不作为索引正文，当前仅索引标题、Markdown 正文，summary 参与源版本和关键词兜底。

## 在线模型配置

Docker `.env.docker` 和本地 `zdblog-master/.env` 使用以下配置；将 Workspace ID 和 API Key 替换为百炼控制台中的实际值：

```dotenv
RAG_ENABLED=true
RAG_EMBED_PROVIDER=openai
RAG_EMBED_BASE_URL=https://<WorkspaceId>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
RAG_EMBED_API_KEY=<DashScope API Key>
RAG_EMBED_MODEL=qwen3.7-text-embedding-flash
RAG_EMBED_DIM=1024
RAG_EMBED_SEND_DIMENSIONS=true
```

`RAG_EMBED_BASE_URL` 中的地域端点要与百炼 Workspace 区域一致。Flash 接口每次最多接收 20 条文本，代码批次上限已设为 20。当前本地 `BAAI/bge-small-zh-v1.5` 输出 512 维，不兼容新的 1024 维 schema；切换回本地推理需要另选 1024 维模型并重建索引。

配置 defaults 在 `rag/config.py`，由 `config/settings.py` 在读取环境变量后导入。默认 chunk 400 字，overlap 60，top-k 5，候选 20，片段 300 字，工具返回总预算 1,500 字。当前阈值 `RAG_MIN_DENSE_SCORE=0.56`、`RAG_MIN_LEXICAL_SCORE=0.45` 是旧本地 BGE 模型的校准值，切换到 Qwen 后应使用本站金标重新评估；RRF 分数不能充当概率或置信度。

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

迁移 `0002_embedding_1024` 将派生向量列改为 `vector(1024)`，清除旧向量并将索引标记为待更新，不修改文章正文。升级后运行 `python manage.py rag_reindex --prune` 重建全部公开文章索引；模型 API key 或 Workspace URL 未配置时，文章会保持词法检索状态。

## 验证与限制

```powershell
python manage.py test rag chat_robot --settings=rag.test_settings --noinput
python manage.py makemigrations --check --dry-run
```

测试使用独立的 `test_zdblog_rag` PostgreSQL 库，真实创建扩展和 `vector(1024)` 列。embedding 在测试中替换为确定向量，不调用在线模型或 DeepSeek；原聊天迁移测试继续使用独立 SQLite 连接。不要把 SQLite 测试结果当作 pgvector 集成验证。

2026-10-03 的本地 BGE 实测（512 维）只作为旧模型基线：当时首次索引覆盖 9 篇公开文章、27 个正文块；13 条金标的 Recall@5、HitRate@5、MRR、负例正确率均为 1.0。该小样本结果不代表新 Qwen 模型的检索效果；切换后应重新运行 `rag_eval` 并校准阈值。

这些数据同时用于阈值校准，属于小样本回归验证，不是独立测试集；不代表所有未知话题的准确率，也没有衡量返回列表中其余文章的 precision。此轮未调用在线 DeepSeek 验证最终回答质量，已验证真实本地 embedding、PostgreSQL 检索、引用格式及 Agent 工具循环。

同步索引让文章保存额外调用在线嵌入 API；其可用性、限流和网络延迟会影响文章保存和检索体验。API 凭证应放在服务器环境文件中，不要写入仓库或日志。启动环境更改后需重建后端容器。

工具结果通过完整链接分配字符预算，不在 URL 中间截断；1,500 个中文字符可能超过 4.5KB，JSON 和 Markdown 还有额外开销。展示历史中的旧引用/工具消息不会因文章后来设为私密而自动删除，新检索已按当前公开状态过滤。

长代码围栏可被递归切开，rerank、异步任务队列和检索 API 页面尚未加入。当前实现支持自然语言/术语混合检索，不保证未知话题 100% 判空；实际指标须以本站金标和模型实测结果为准。后台改工具配置默认只影响新会话；本次迁移对已有“博客助手”聊天做了一次明确升级。
