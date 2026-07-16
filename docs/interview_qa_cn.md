# BidGuard AI 中文面试问答题库

这份题库基于当前仓库的真实实现和实测结果编写，适合中国市场的 AI 应用工程师、RAG 工程师、Python 后端工程师和全栈 AI 岗位。回答重点不是背技术名词，而是讲清楚问题、设计、取舍、验证和局限。

## 使用方法

1. 先掌握 30 秒和 2 分钟介绍，不要一开始就倾倒全部技术细节。
2. 每道题先回答“结论”，再根据面试官兴趣展开实现、指标和失败案例。
3. 数字必须区分工作流回归集和检索挑战集，不能把 `36/36` 说成系统准确率 100%。
4. 主动承认合成数据、规则抽取、无 OCR 等边界，比把作品包装成商业法律产品更可信。
5. 面试前至少亲自演示一次上传、Q&A、拒答、风险检查、文档比较和 Agent Trace。

## 三套项目介绍

### 30 秒版本

BidGuard AI 是一个 evidence-first 的招投标和合同文档审查 Agent。它支持 PDF、DOCX 和 TXT 上传，通过 FastAPI 完成解析、分块、字段抽取和持久化，使用 PostgreSQL pgvector 与真实 embedding 做检索，再由 DeepSeek 在证据充足时进行受约束生成。系统不仅做文档问答，还包括确定性风险规则、跨文档条款比较、工具调用 Trace 和评估体系。核心特点是答案必须附带页码和 chunk 证据，证据不足时会跳过 LLM 并固定拒答。

### 2 分钟版本

这个项目解决的不是“让模型读 PDF”这么简单的问题，而是如何让文档审查结果可追溯、可拒答、可评估。上传文档后，PDF 通过 PyMuPDF 按页解析，DOCX 从 Word XML 提取文本，随后按每页 180 个词、35 个词 overlap 分块，并保存 document id、page number、chunk index 和 embedding 元数据。

本地零配置模式使用 SQLite、确定性 hash embedding 和 fake LLM，保证测试稳定；真实演示模式使用 Ollama `embeddinggemma`、PostgreSQL pgvector 和 DeepSeek `deepseek-v4-flash`。检索不是只看向量相似度，而是结合关键词、领域短语、语义相似度和文档版本约束。检索结果先经过 evidence sufficiency gate，过滤 prompt injection、低分结果和缺少真实标识符的证据；只有通过门控才调用 LLM，否则返回固定的 insufficient-evidence 文案。

Agent 是轻量工具路由，不是多 Agent 系统。它会根据目标调用 evidence search、risk rule check、cross-document diff 或 report generator，并记录输入、输出、延迟和 evidence count。评估方面，我做了 36 条工作流回归和 16 条独立检索挑战。真实 Provider 工作流通过 36/36，但检索挑战的 Recall@5 是 `0.6875`、MRR 是 `0.6250`，还保留了 5 个语义难例。这说明我不仅展示成功路径，也记录真实失败和下一步实验方向。

### 5 分钟版本的讲述顺序

1. 业务问题：普通 PDF Chatbot 会隐藏检索质量并可能生成无证据答案。
2. 数据流：上传、解析、按页分块、embedding、存储、检索、门控、生成、引用。
3. 双运行模式：SQLite/local 用于零配置测试，PostgreSQL/pgvector/真实 Provider 用于现实验证。
4. 工具能力：风险规则、字段抽取、版本比较、报告导出、Trace。
5. 质量证明：测试、CI、Provider smoke、pgvector smoke、36 条工作流 eval、16 条检索 benchmark。
6. 真实局限：小型合成语料、规则抽取、无 OCR、无像素级 PDF 高亮、Recall@5 仍有提升空间。

---

## 一、项目定位与个人贡献

### 1. 请介绍一下 BidGuard AI。

**回答：**

BidGuard AI 是一个面向公开招标文件和合同草案的证据优先文档审查应用。用户可以上传 PDF、DOCX 或 TXT，系统会解析和分块文档，提取常见采购字段，回答带页码证据的问题，执行确定性风险检查，比较两个文档版本，并展示 Agent 实际调用了哪些工具。

它的核心不是“生成一段看起来合理的文字”，而是建立一条可审计链路：回答来自哪些 chunk、位于哪一页、检索分数是多少、使用什么 Provider、是否调用 LLM、工具耗时多少。证据不足时，后端返回固定拒答文本并跳过 LLM。

### 2. 这个项目解决了什么真实问题？

**回答：**

合同和招标审查经常需要反复定位付款期限、投标截止时间、验收标准、责任限制、争议解决和终止条件。普通关键词搜索难以处理同义表达，普通聊天机器人又可能把模型推断包装成文档事实。

BidGuard AI 将问题拆成三类：可检索事实用 evidence Q&A；结构化风险信号用确定性规则；版本变化用字段和条款 Diff。这样既利用 LLM 的语言能力，又把可确定的逻辑留在可测试代码中。

### 3. 为什么它不只是一个 PDF Chatbot？

**回答：**

它比 PDF Chatbot 多了五层工程能力：第一，保存页码、chunk id 和检索元数据；第二，LLM 前有证据充足性门控；第三，存在独立的风险规则和跨文档比较工具；第四，Agent Run 和 Tool Call 会持久化；第五，有独立评估集、检索 benchmark、Provider smoke 和 pgvector smoke。

如果只做 PDF Chatbot，演示往往停留在“上传后能聊天”。这个项目可以回答“为什么相信这次结果”“检索错在哪里”“为什么这次没有调用模型”和“改动后指标是否回归”。

### 4. 你在项目中具体做了什么？

**回答：**

这是个人项目，我负责需求边界、FastAPI API、SQLAlchemy 数据模型、Alembic 迁移、PDF/DOCX/TXT 解析、chunking、embedding 与 LLM Provider 抽象、pgvector 检索、证据门控、Agent 工具、评估脚本、Next.js 前端、Docker、CI 和文档。

面试时不要只说“全栈都是我做的”，要举两个具体问题。例如真实 Provider eval 首次只有 31/36，其中缺失 tax ID 的问题虽然最终拒答，但弱语义证据仍进入了 DeepSeek。我增加了 identifier-aware gate，要求证据包含明确标签和值，否则直接拒答并跳过 LLM。另一个问题是 pgvector 异常被静默 fallback，我改成记录明确 fallback reason，并让严格 benchmark 在缺少 pgvector 时失败。

### 5. 为什么选择招投标和合同审查场景？

**回答：**

这个场景适合展示 RAG 的核心价值，因为答案通常可以定位到具体页和条款，天然需要证据引用；同时它还包含字段抽取、风险规则和版本比较，不会退化成通用聊天界面。

我刻意将项目定位为工程演示而不是法律产品。风险规则只是常见采购信号，输出中保留证据和 disclaimer，不声称替代律师或保证识别全部风险。

### 6. 项目的主要技术栈是什么？为什么这样选？

**回答：**

前端使用 Next.js、TypeScript 和 Tailwind CSS，后端使用 FastAPI、Pydantic、SQLAlchemy 和 Alembic。SQLite 支持零配置演示，PostgreSQL 加 pgvector 支持真实向量检索。PDF 使用 PyMuPDF，embedding 和 LLM 使用 OpenAI-compatible Provider 抽象，真实演示分别接 Ollama `embeddinggemma` 和 DeepSeek。

这套选择的重点是边界清楚：FastAPI 适合类型化 AI API；SQLAlchemy 让 SQLite 与 PostgreSQL 共用模型；Provider 抽象避免业务代码绑定单一厂商；Next.js 适合快速完成可演示的证据面板和 Trace UI。

### 7. 项目的最大亮点是什么？

**回答：**

最大亮点是“证据门控加真实评估”，而不是用了某个模型。系统会把 prompt injection chunk 排除，要求结果满足关键词、短语或语义阈值，对 tax ID 等标识符问题额外验证证据里确实存在标签和值。未通过时不会把弱上下文交给 LLM。

同时我没有只展示 36/36。独立检索挑战中，真实 pgvector Recall@5 是 `0.6875`，仍有 5 个 hard semantic miss。这个结果更能说明我理解回归测试和泛化检索质量的区别。

### 8. 如果现场只能演示三分钟，你会展示什么？

**回答：**

第一步问一个可回答问题，例如 solar microgrid 的 bid deadline，展示最终答案、page、chunk、score、`retrieval_method=pgvector` 和 LLM synthesis 状态。第二步问不存在的 vendor tax ID，展示固定拒答、零 evidence 和 LLM skipped。第三步打开 Agent Trace 或比较原合同与修订合同，证明系统不只是聊天界面。

如果还有时间，再展示 `demo_risky_terms` 的 120 天付款、模糊验收和缺失争议解决。不要用正常 tender 演示风险规则，否则简单规则可能出现不理想的误报。

---

## 二、系统架构与后端设计

### 9. 请讲一下系统整体架构。

**回答：**

前端通过 REST API 调用 FastAPI。上传请求进入 parser，根据格式生成带页码的 page records；chunker 在页内生成重叠 chunk；embedding Provider 批量生成向量；SQLAlchemy 保存文档、chunk、字段和 Provider 元数据。PostgreSQL 模式还会写入 `embedding_vector`。

查询时先生成 query embedding。PostgreSQL 使用 pgvector cosine distance 取候选，SQLite 则在 Python 侧计算相似度和混合分。候选经过关键词、领域短语、文档版本和安全门控，证据充分时调用 guarded LLM，否则固定拒答。Agent、风险检查、Diff 和报告工具共享这些存储结果，并将运行记录写入 `agent_runs` 和 `tool_calls`。

### 10. 为什么后端选择 FastAPI？

**回答：**

FastAPI 对这个项目的优势是 Pydantic 请求校验、自动 OpenAPI、依赖注入和清晰的同步数据库 Session 生命周期。AI 工程中输入结构经常变化，强类型 schema 能减少前后端契约错误，也便于 smoke test 直接调用 API。

它不是因为“FastAPI 比所有框架都快”。当前主要耗时来自 embedding 和 LLM 网络调用，框架吞吐不是瓶颈。如果进入高并发生产环境，我会进一步把长耗时 ingestion 放入任务队列，并使用 async HTTP client 或 worker，而不是只依赖框架性能。

### 11. 为什么前端选择 Next.js？

**回答：**

项目需要文档列表、动态详情页、Q&A、风险审查、Diff 和 Agent Trace，多页面路由和 TypeScript API 类型比较重要。Next.js App Router 可以自然组织这些页面，Tailwind 便于保持一致的信息密度和响应式布局。

这个项目没有强行加入 Server Actions 或复杂 SSR。数据来自独立 FastAPI，因此前端保持简单 fetch wrapper；重点是把证据、状态、错误和工具 Trace 展示清楚。

### 12. 后端如何划分模块？

**回答：**

`api/routes.py` 负责 HTTP 契约和状态码，`models.py` 管理数据库实体，`schemas.py` 管理请求模型。解析、分块、embedding、retrieval、LLM、risk、field extraction、diff、agent 和 reporting 分别放在 service 模块中。evaluation 目录负责指标和 runner，scripts 目录提供可重复 smoke 命令。

这种划分允许我独立测试纯函数，例如 chunking、字段抽取、风险规则和检索评分；Provider 也可以通过 fake response 测试，不需要真实 API Key。

### 13. 主要 API 有哪些？

**回答：**

核心接口包括 `/api/health`、`/api/dashboard`、`/api/documents/upload`、`/api/documents`、`/api/documents/{id}`、`/api/documents/{id}/report`、`/api/qa`、`/api/risk-check`、`/api/diff`、`/api/agent/run` 和 `/api/agent/runs`。

开发评估还使用 `/api/dev/seed-text-document` 注入可重复的 synthetic pages。面试时要说明这是开发/评估辅助接口，真实公开部署应关闭、加环境开关或单独保护，不能把它当成生产接口。

### 14. 数据库有哪些核心表？

**回答：**

`documents` 保存文件元数据和解析状态；`document_chunks` 保存文本、页码、chunk index、JSON embedding、Provider 元数据和 PostgreSQL vector；`extracted_fields` 保存字段值、页码、置信度和证据；`risk_findings` 保存规则、类别、严重度和证据。

`agent_runs` 保存一次目标执行，`tool_calls` 保存按顺序发生的工具输入、输出和延迟。还预留了 `document_tables`、`eval_cases` 和 `eval_results`，但当前 eval 数据主要使用版本控制下的 JSON，不能声称预留表已经形成完整在线评估平台。

### 15. 为什么同时支持 SQLite 和 PostgreSQL？

**回答：**

SQLite 解决可运行性：没有 Docker、pgvector 或 API Key 也能启动项目和跑测试。它保存 JSON embedding，并在 Python 中执行 hybrid fallback。PostgreSQL 解决真实性：pgvector 在数据库内执行向量距离排序，适合展示真正的向量检索路径。

我明确把 SQLite 描述为 fallback，不把 Python 侧 hash vector 检索包装成生产语义搜索。两条路径共用 SQLAlchemy 模型和 Provider 接口，因此测试便利性与真实演示可以兼得。

### 16. SQLAlchemy 和 Alembic 分别负责什么？

**回答：**

SQLAlchemy 定义运行时实体关系和 Session 操作；Alembic 保存可审计的 schema 演进，包括初始表、embedding metadata、pgvector column 和 risk category。

MVP 为了 SQLite 开箱即用，启动时还会调用 `create_all` 和小范围 runtime schema compatibility。商业化时我会移除自动 DDL，强制 migration-first，并让部署流水线在应用启动前执行 Alembic，避免多个实例同时改 schema。

### 17. 数据库事务和异常是如何处理的？

**回答：**

FastAPI 的 `get_session` dependency 在请求成功后 commit，异常时 rollback。上传过程在一个 Session 中创建 document、chunks、embedding metadata 和 extracted fields；如果 embedding Provider 抛出 `EmbeddingError`，API 返回 503，Session dependency 会回滚数据库写入。

当前文件会先写到 upload directory，再完成数据库事务，因此极端失败可能留下 orphan file。这是已知工程改进点：生产实现应写临时文件，事务成功后原子重命名，或在异常路径清理文件，并增加大小限制和对象存储。

### 18. 为什么当前 API 大部分是同步函数？

**回答：**

项目的 SQLAlchemy Session 是同步模式，数据规模和并发目标是个人演示，因此保持同步可以降低复杂度。上传读取使用 async，但 embedding 和 LLM 的 httpx 调用目前也是同步 client。

如果目标变成多用户服务，我会把 ingestion 和批量 embedding 放到队列 worker，API 返回 job id；Q&A 可以改用 async HTTP client，并根据数据库驱动决定是否使用 async SQLAlchemy。不能只把函数改成 `async def`，否则同步网络调用仍会阻塞 event loop。

### 19. 如何管理配置和密钥？

**回答：**

配置由 Pydantic Settings 从环境变量和 `backend/.env` 读取，包含 database URL、upload path、CORS、Provider、model、dimension、timeout 和成本单价。`.env`、本地数据库、uploads、eval reports 和 build artifacts 都被 `.gitignore` 排除。

测试和 CI 显式使用 local Provider，不依赖真实密钥。真实 DeepSeek key 只保存在 ignored `.env` 或 shell。文档示例只使用 placeholder，Provider smoke 在缺少 key 时显示 skipped，而不是伪造通过。

### 20. CORS 和前后端 API 地址如何处理？

**回答：**

后端从 `CORS_ORIGINS` 读取允许来源，默认本地前端是 `http://localhost:3000`。前端通过环境变量配置 API base URL，避免把部署地址写死在组件中。

当前 CORS 只是本地开发配置，不等于身份认证或权限控制。公开部署还需要 HTTPS、认证、授权、速率限制和更严格的 origin 管理；不能把 CORS 当作安全边界。

---

## 三、文档解析、分块和字段抽取

### 21. 系统支持哪些文档格式？

**回答：**

当前支持 PDF、DOCX 和 UTF-8 TXT。PDF 保留真实页码，TXT 作为单页文本，DOCX 目前从 `word/document.xml` 提取段落并作为 document-level page 1。上传接口同时检查 MIME type 和扩展名，并对不支持格式返回 400。

当前没有 OCR，所以扫描型 PDF 可能只有空文本；也没有解析 Word comments、tracked changes、复杂表格或真实分页。面试时必须明确这一点。

### 22. PDF 是如何解析的？

**回答：**

后端使用 PyMuPDF，也就是 `fitz`。文件以 bytes 形式打开，逐页调用 `page.get_text("text")`，生成 `{page_number, text}`。即使某页为空，也保留页记录；如果文件无法打开或完全没有页面，会返回明确的 ValueError，再由 API 转成 400。

选择 PyMuPDF 是因为依赖较轻、按页提取方便、适合 MVP。它不保证恢复复杂阅读顺序，面对多栏、表格、扫描页时需要 layout parser 或 OCR，这是后续方向。

### 23. DOCX 为什么不使用 python-docx？

**回答：**

当前需求只是轻量文本提取，所以直接把 DOCX 当 ZIP，读取 `word/document.xml`，使用标准库 ElementTree 遍历 paragraph 和 text node。这样没有新增重依赖，也容易测试损坏 ZIP、缺失 XML 和空文档错误。

代价是只得到段落文本，没有 Word 页码、样式、表格、批注和修订记录。如果要做正式合同审查，我会考虑 python-docx 加底层 XML 处理，或 LibreOffice/布局解析服务，但不能声称当前实现支持这些能力。

### 24. Chunking 策略是什么？

**回答：**

系统按页处理，每个 chunk 默认 180 个 whitespace words，重叠 35 个词。chunk 不跨页，因此引用页码天然稳定；每个 chunk 保存 document id、全局 chunk index、page number、text 和 token_count。

这不是模型 tokenizer 意义上的 token，而是 `split()` 后的词数。选择简单确定性策略是为了让回归测试稳定。中文或复杂版式下 whitespace chunking 不够好，后续应使用语言感知或 tokenizer-aware chunking，并重新评估而不是直接替换。

### 25. 为什么需要 overlap？

**回答：**

条款可能刚好跨越 chunk 边界。35 个词 overlap 可以让边界附近的上下文出现在相邻 chunk 中，降低关键句被切断后无法检索的概率。

Overlap 的代价是存储和 embedding 计算重复，也可能让相似 chunk 同时占据 top-k。更大语料下可以加入去重或 MMR，但当前 corpus 小，先保留简单可解释策略。

### 26. 为什么 chunk 不跨页？

**回答：**

因为项目强调 page-level evidence。如果 chunk 横跨两页，就必须保存页范围并处理引用展示；按页切分让每个证据只有一个明确 page number，也便于点击回 document detail。

缺点是跨页条款可能丢失连接。生产方案可以保存 `page_start/page_end`，或者让 retrieval context 在命中 chunk 后附加前后相邻 chunk，同时保持原始 citation 边界。

### 27. 系统提取哪些字段？

**回答：**

当前提取 project name、buyer、supplier、bid deadline、opening time、contract amount、payment terms、delivery date、acceptance criteria、liability clause 和 dispute resolution clause。每个字段保存 value、page number、confidence 和 evidence text。

字段抽取使用多组 regex 和采购常见同义标签，例如 `Project Title`、`Procuring Entity`、`Vendor`、`Closing date`、`Net 45 days`。这是可解释 baseline，不是通用信息抽取模型。

### 28. 字段抽取的 confidence 是怎么来的？

**回答：**

当前 confidence 是启发式值：有明确冒号标签的匹配通常是 `0.65`，较宽松的文本模式是 `0.45`，没找到是 `0.0`。它表示规则匹配强弱，不是经过概率校准的真实置信度。

面试时不能说“准确率 65%”。如果要做可信 confidence，我会构建人工标注字段集，按字段测 precision、recall、exact match，再用匹配类型、模型 score 和文档布局训练或校准置信度。

### 29. Cross-document diff 是怎么实现的？

**回答：**

系统先对两个文档独立抽取同一组字段，然后对 value 做 lowercase 和 whitespace normalization。两个值都有且标准化相等则是 `same`；两个值都有但不同则是 `changed`；任意一方缺失则是 `uncertain`。

返回行同时包含两侧 value、page 和 confidence。这样前端不会把“没抽出来”误报成“条款已删除”。局限是它比较字段值，不是任意段落级 semantic diff；复杂修订需要 clause alignment 和结构化 redline。

### 30. Markdown review report 包含什么？

**回答：**

报告按文档生成，包含文件和页数、重要边界说明、抽取字段、风险发现及证据、最多 20 个 evidence chunk 索引。风险按 high、medium、low 和 rule name 排序，并明确声明它不是专业法律建议。

选择 Markdown 是为了依赖轻、可下载、可版本化。当前不是 PDF 报告引擎，也没有模板审批、电子签名或法律意见书格式。

---

## 四、Embedding、检索与 pgvector

### 31. 什么是这个项目中的 RAG？

**回答：**

RAG 在这里分为 ingestion 和 query 两条链路。Ingestion 将文档解析成 chunk，生成 embedding 并保存；query 将问题转为 embedding，检索候选证据，经过门控后把有限证据交给 LLM 生成答案。

关键点是 LLM 不直接读取整个数据库，citation 也不是模型自己编造。后端先决定哪些 chunk 可用，模型只负责基于这些 chunk 组织自然语言答案。

### 32. Local deterministic embedding 是什么？

**回答：**

Local Provider 对 token 做稳定 hash，将值映射到固定维度向量，再做归一化。相同输入始终产生相同结果，不需要模型和 API Key，适合单元测试、CI 和零配置演示。

它不是语义 embedding，不能可靠理解 `financial exposure` 和 `liability cap` 这类同义关系。README 将它标记为 local fallback，而不是宣传为真实语义检索。

### 33. 真实 embedding 为什么使用 Ollama？

**回答：**

Ollama 在本机运行 `embeddinggemma`，并暴露 OpenAI-compatible embeddings API。这样不需要额外 embedding API Key，可以验证真实模型、HTTP Provider、dimension、PostgreSQL vector 写入和检索，同时避免把所有 Provider 都绑定到云服务。

它的外部 API 费用为 0，但本地计算、电力和硬件并非真正免费。面试时说“无外部 API 成本”比“完全免费”更准确。

### 34. Provider abstraction 是怎么设计的？

**回答：**

Embedding Provider 统一暴露 `embed_texts()`、provider name、model、dimension 和 last_call metrics。实现包括 local deterministic 和 OpenAI-compatible。LLM Provider 统一负责 evidence-only synthesis，也有 local fake 和 OpenAI-compatible 实现。

业务 service 只调用接口，不关心是 Ollama、DeepSeek 还是其他兼容服务。真实 Provider 只有在被选中并实际调用时才校验 key/base URL；local 模式零配置。响应维度、HTTP 状态、超时和 response shape 都会产生可读错误。

### 35. PostgreSQL pgvector 路径是如何工作的？

**回答：**

迁移会启用 vector extension，并按 `EMBEDDING_DIMENSION` 创建 `embedding_vector vector(n)` 和 ivfflat cosine index。上传时 chunk 同时保存 JSON embedding metadata，并在 PostgreSQL 中将同一向量 cast 到 vector column。

查询时使用 `<=>` cosine distance，按 `1 - distance` 得到 similarity，先在数据库取候选，再进入统一的 hybrid scoring 和 evidence filter。Smoke script 会验证 extension、column type、stored vector count、`retrieval_method=pgvector` 和拒答行为。

### 36. 为什么还保留 JSON embedding？

**回答：**

JSON embedding 让 SQLite 与 PostgreSQL 共用模型，也保存 Provider 结果用于 fallback、调试和 benchmark。PostgreSQL 的 `embedding_vector` 负责数据库向量检索，JSON 字段不是 pgvector 的替代。

生产环境如果存储压力显著，可以只在特定数据库保留原始 vector column，并把 Provider metadata 单独列化；当前双存储是为了兼容和可观测性。

### 37. Hybrid retrieval 的分数如何计算？

**回答：**

先对问题和文本做 lowercase alphanumeric tokenization并去除英文 stopwords。关键词分数来自 token overlap 加领域短语 bonus，再除以 unique query token 数。有 query embedding 且存在关键词命中时，基础分是 `0.6 * keyword_score + 0.4 * similarity_score`。

如果没有关键词命中，只有真实语义 Provider 和真实检索方法才允许直接使用 similarity；local hash 的纯语义分只乘 `0.05`，防止随机 hash 相似度伪装成语义证据。最后文档版本 scope score 以 `0.25` 权重加到分数上。

### 38. 为什么关键词权重比向量高？

**回答：**

当前合同字段常包含精确标签、日期和金额，关键词命中对这些问题非常可靠；同时使用的小型 embedding 和 synthetic corpus 并不保证语义分足够稳定，因此采用偏保守的 60/40。

这不是通用最优值。权重应通过验证集搜索或学习排序决定。当前项目保留 benchmark，任何调整都应该比较 Recall@k、MRR、page hit、latency 和 hard negatives，而不是凭感觉改参数。

### 39. 文档版本约束解决了什么问题？

**回答：**

原合同和修订合同通常高度相似。早期 eval 中，问题明确问 original draft，但修订条款因为语义更近而排在前面。系统因此识别 `original contract`、`contract draft`、`revised contract`、`addendum` 等范围词。

匹配目标版本加 `2.0` scope，错误版本减 `2.0`，再以 `0.25` 加入最终分。还处理 `not the revised` 的否定，避免同时识别为 revised。这个分数表示显式文档范围约束，不是普通关键词 bonus。

### 40. 如果 pgvector 查询失败会怎样？

**回答：**

运行时可以 fallback 到 Python hybrid retrieval，但会记录 `retrieval_fallback_reason` 并写 warning，不能静默假装仍使用 pgvector。严格 benchmark 使用 `--require-pgvector`，缺失或 fallback 会直接失败。

这种设计区分 availability 和 experiment integrity：线上查询可以降级保持可用；评估脚本必须 fail closed，防止报告把 fallback 结果标成 pgvector 成绩。

### 41. 为什么 64 维反而比 768 维效果好？

**回答：**

`embeddinggemma` 原生报告 768 维，但在这套 16 条小型挑战集上，64 维实验 Recall@5 是 `0.6875`、MRR 是 `0.6250`，768 维分别是 `0.6250` 和 `0.5938`。这只说明该模型、压缩方式、语料和评分组合下，维度更大没有自动带来更好排序。

不能据此得出“64 维普遍优于 768 维”。样本很小，结果可能受 query encoding、索引、混合权重和标签影响。正确做法是扩大人工标注数据，使用模型推荐的 query/document encoding，再决定维度。

### 42. 为什么现在没有加 reranker？

**回答：**

我先建立 baseline 和 failure analysis，再决定是否增加组件。真实 embedding 将 Recall@5 从 `0.5625` 提高到 `0.6875`，但 5 个语义难例仍失败。下一步先测试 query expansion、领域短语和模型推荐编码；如果 reranker 能在相同数据上显著提高 Recall/MRR，且延迟可接受，再加入为独立 benchmark row。

如果没有评估就加 reranker，只是让架构图更复杂，无法证明收益。面试官通常更认可“测量后做取舍”而不是堆模型。

---

## 五、Evidence-first、LLM 与安全门控

### 43. Evidence sufficiency gate 具体检查什么？

**回答：**

候选首先过滤被识别为 prompt injection 的 chunk 和低于 `min_score` 的结果。之后要求存在关键词命中，或者结果来自真实语义路径、真实 Provider 且 similarity 至少 `0.55`。包含 keyword coverage 的结果还要满足以下之一：semantic match、领域 phrase match、coverage 至少 `0.5`，或 keyword score 至少 `0.75`。

对于 tax ID、certificate number、serial number 等标识符问题，还有额外 value gate：证据必须匹配明确标签和值，`missing`、`not provided`、`unknown` 等不能作为答案依据。

### 44. 为什么不能只设置一个相似度阈值？

**回答：**

单一向量阈值无法区分精确字段、语义改写和偶然相似。比如供应商信息可能与 tax ID 问题语义相关，但并不包含 ID 值；如果只看 similarity，就可能把弱上下文交给 LLM。

因此系统同时使用 query-aware 规则、关键词覆盖、领域短语、Provider 类型和标识符值检测。代价是规则更复杂、偏英文领域，需要通过 eval 防止过拟合。

### 45. 证据不足时系统做什么？

**回答：**

后端返回完全固定的英文句子：`The uploaded documents do not contain enough evidence to answer this question reliably.`，evidence 为空、confidence 为 0、`llm_synthesis_used=false`、provider usage 为空。

实际 Q&A 响应仍会标明当前配置的 synthesis provider，便于观测运行模式，但 `provider_usage` 为空且不会发起 LLM 请求。因此判断是否调用模型应看 `llm_synthesis_used` 和 usage，而不是只看 provider 名称。

固定文本便于前端处理和自动化回归，更重要的是 LLM 根本不会被调用。拒答不是让模型“尽量说不知道”，而是后端在模型边界之外做确定性决定。

### 46. 如何防止模型编造 citation？

**回答：**

citation 对象由后端 retrieved chunks 生成，不让 LLM 自由产生 document id、page 或 chunk id。LLM 只返回 answer text，最终 API 仍附上经过门控的原始 evidence list。

Provider smoke 还会检查模型是否输出未提供的 bracket citation。更强的生产方案可以让模型返回 evidence id 列表，并验证每个 id 属于本次候选，或者逐句做 entailment/faithfulness 检查。

### 47. Guarded LLM prompt 的设计原则是什么？

**回答：**

System prompt 明确要求仅使用提供的 evidence，不使用外部知识；证据片段带有稳定编号和 source metadata；问题和证据分隔；如果证据不能回答，应返回固定 fallback。Temperature 设置为 0，减少同一证据下的输出波动。

Prompt 只是第二层防线。第一层仍是后端 evidence gate，因为模型可能不完全遵守“不要回答”。安全设计不能只依赖提示词。

### 48. 为什么 LLM 使用 DeepSeek？

**回答：**

项目通过 OpenAI-compatible 接口接入 DeepSeek，主要验证真实 hosted LLM、token usage、cache usage、latency 和成本记录。业务层不依赖 DeepSeek 特有 SDK，因此可以替换其他兼容 Provider。

模型选择不是项目核心卖点。面试时重点应放在模型前后的检索、门控、观测和评估，而不是说“因为 DeepSeek 更聪明”。

### 49. 如何记录 LLM 和 embedding 的成本？

**回答：**

Provider 的 `last_call` 记录 provider、model、latency、input/output/total tokens 和 estimated cost。DeepSeek 还区分 cache-hit 与 cache-miss input tokens，成本根据配置的每百万 token 单价计算。Embedding ingestion 和 query usage 分开收集，再在 eval 汇总。

2026-07-10 的 36 条真实工作流共记录 7,318 provider tokens，估算 DeepSeek 成本 `$0.00062828`。价格会变化，所以文档同时记录成本基准日期和配置，而不把金额当永久结论。

### 50. Prompt injection 是如何处理的？

**回答：**

当前实现使用 regex 检测文档中的典型指令，例如忽略系统指令、泄露 system prompt、要求伪造答案或 citation。命中的 chunk 会保留检测标记，但在 `filter_usable_evidence` 阶段被排除，不进入答案和 LLM context。

这只是 baseline，无法覆盖编码、间接指令和更复杂攻击。生产方案需要内容与指令分离、结构化 prompt、来源信任策略、输出验证和更完整 adversarial eval。

### 51. 如果 embedding API 超时或返回错误怎么办？

**回答：**

OpenAI-compatible Provider 会把 missing key、base URL、HTTP error、timeout、非法 JSON、空向量和 dimension mismatch 转成可读 `EmbeddingError`。上传阶段 embedding 失败返回 503，不会静默保存“已完成但无 embedding”的文档。

查询阶段可以记录失败原因并退回关键词检索，从可用性角度继续服务；严格 Provider smoke 和 real benchmark 则必须失败。不同场景采用不同 fail-open/fail-closed 策略。

### 52. 为什么 temperature 设置为 0 仍不能保证事实正确？

**回答：**

Temperature 0 主要降低随机性，不会自动让模型理解正确，也不能修复错误检索。如果输入 evidence 错了，模型仍可能稳定地产生错误答案；如果 prompt 有漏洞，也可能稳定地越界。

事实可靠性来自 retrieval quality、evidence gate、citation binding 和 eval，不是单个 sampling 参数。

---

## 六、Agent、风险规则与工具 Trace

### 53. 这个 Agent 到底做了什么？

**回答：**

它是一个轻量 intent router。提供 document A/B 时走 cross-doc diff；目标包含 risk、review、check 或 report 时调用 risk checker；明确要求 report 时调用 report generator；提供 document ids 时调用 evidence search；证据充足时再调用 guarded LLM synthesis。

每次运行创建 AgentRun，每个工具创建 ToolCall，记录输入、输出、latency、status 和 evidence count。它展示的是可追踪工具编排，不是自治规划或自我反思 Agent。

### 54. 为什么没有使用 LangGraph 或多 Agent？

**回答：**

当前工作流分支有限，简单条件路由更容易测试和解释。引入 LangGraph 或多 Agent 会增加状态管理、循环终止、成本和调试复杂度，但不一定提高结果。

如果未来出现长流程，例如多轮补充检索、人工审批、失败恢复和 checkpoint，再考虑状态图。技术选型应由工作流复杂度驱动，而不是为了简历堆框架。

### 55. Agent Trace 有什么价值？

**回答：**

Trace 可以回答一次结果到底走了哪条路径：是否检索、是否执行风险规则、是否调用 LLM、调用顺序、每步耗时和证据数量。它有助于演示、排错和评估 tool-call accuracy。

当前 Trace 是应用级可观测性，不是完整分布式 tracing。生产环境还需要 request id、structured logs、OpenTelemetry、敏感字段脱敏和跨服务 trace。

### 56. 风险检查包含哪些规则？

**回答：**

当前有八类演示规则：付款期限超过 90 天、验收标准模糊或缺失、责任条款只约束一方、终止条件不清楚、投标截止与开标时间疑似不一致、资格要求过度指定、评分标准未量化、缺失争议解决条款。

每个 finding 包含 rule name、category、severity、explanation、evidence text 和 page number。规则结果会持久化，重复运行前会清理当前文档旧 findings，避免重复累积。

### 57. 为什么风险检查使用规则而不是 LLM？

**回答：**

付款天数、缺失条款、百分比评分等信号可以用确定性规则稳定检测，容易写测试，也不会因为模型温度或版本产生漂移。LLM 更适合对已有证据做解释，而不是替代所有业务判断。

规则缺点是覆盖有限和容易误报，因此 UI 显示原始 evidence，项目明确称其为 review signal 而不是法律结论。未来可以采用规则召回、模型复核、人工确认的分层方案。

### 58. 当前风险规则有没有误报？

**回答：**

有可能。最明显的例子是当前“deadline 与 opening time 不一致”规则只要两个文本值不同就触发，但真实招标中开标晚于截止时间通常是正常的。它能检测极端不一致，却缺少日期解析、时区和允许窗口判断。

面试时我会主动承认并给出修复设计：用 datetime parser 标准化两个时间，只有 opening 早于 deadline、跨时区冲突或超过业务允许窗口时才告警；同时增加正负样本。承认这个局限比把所有规则结果称为准确风险更专业。

### 59. 风险规则如何处理“缺失”而不是“异常”？

**回答：**

例如 dispute resolution 规则会在全文没有 dispute、arbitration、court、jurisdiction 或 mediation 信号时产生 high finding，evidence 和 page 可以为空，解释为文档中没有足够证据。

缺失型 finding 与命中型 finding 不同：前者证明的是“没有检出”，不是证明法律上绝对不存在。复杂文档可能使用未覆盖同义词，所以生产版本要有更丰富术语、结构识别和人工复核。

### 60. Agent 运行失败时如何记录？

**回答：**

工具调用测量 latency 并保存 output payload。API 视图根据输出中的 success 字段生成 status，并统计 evidence count。文档不存在等可预期错误转成 404；Provider 和数据库错误不会被空 catch 吞掉。

当前还没有重试队列和 run recovery。生产 Agent 应给每个 tool call 增加 error type、retryable flag、attempt count 和 correlation id，并避免在 trace 中保存密钥或完整敏感合同。

---

## 七、评估、指标与失败复盘

### 61. 项目有哪些评估集？

**回答：**

第一层是 2 条 smoke eval，验证最小 Q&A 和拒答。第二层是 36 条 workflow regression，覆盖 answerable Q&A、insufficient evidence、hard negative、prompt injection、risk、diff 和 agent routing。第三层是独立的 16 条 retrieval challenge，专门比较 keyword、local hash、真实 embedding hybrid 和 pgvector。

把工作流和检索挑战分开很重要：前者检查当前功能是否回归，后者暴露排名泛化问题。不能用同一个“pass rate”模糊两者。

### 62. 36/36 是否代表系统准确率 100%？

**回答：**

不代表。36/36 只说明当前合成回归案例的预期全部满足，包括固定拒答、规则类别、diff 字段和 tool routing。很多案例具有明确标签，部分路径还是确定性规则，因此它证明工程回归稳定，不证明真实合同上的法律准确率。

检索挑战更接近泛化压力测试，真实 Recall@5 只有 `0.6875`。面试时主动区分这两个数字，可以避免过度宣传。

### 63. Recall@k、MRR 和 nDCG@5 分别是什么？

**回答：**

Recall@k 表示带标签的正确 evidence 是否出现在前 k 个结果中，适合判断“有没有召回”。MRR 使用第一个正确结果排名的倒数，正确结果越靠前越好；如果第一名正确得 1，第二名正确得 0.5。nDCG@5 对不同位置的相关性进行折损，并用理想排序归一化，反映前五名整体排序质量。

对证据问答来说，Recall@5 高但 MRR 低意味着证据找到了，却排得太后，可能增加 LLM context 噪声。三者需要一起看。

### 64. 真实检索对照实验结果是什么？

**回答：**

Keyword 和 local deterministic baseline 的 Recall@5 都是 `0.5625`，MRR 是 `0.5208`。Ollama semantic hybrid 64 维和 PostgreSQL pgvector 64 维的 Recall@5 都是 `0.6875`，MRR 是 `0.6250`，nDCG@5 是 `0.6414`。pgvector 平均 query latency 约 `98.110 ms`，keyword 约 `0.159 ms`。

这说明真实语义 embedding 提高了召回和排名，但付出了延迟；pgvector 与 Python semantic hybrid 在小数据集上质量相同，因为候选和统一评分逻辑相近。pgvector 的价值更体现在数据库内检索和可扩展路径，不是小样本下凭空提高模型质量。

### 65. 五个真实 retrieval failure 是什么？

**回答：**

64 维真实语义路径仍漏掉五类目标：original agreement 下的 dispute handling 改写、`financial exposure` 对 liability cap、`hand over` 对 revised delivery、disagreement/forum 对 dispute clause，以及 `end the agreement` 对 termination cure window。

共同问题是领域同义改写与相似文档 hard negative。下一步可以测试 query expansion、领域 synonym mapping、模型推荐 query/document prefix，再评估 reranker。不能通过降低标签要求或把答案关键词塞进查询来“刷分”。

### 66. 为什么 retrieval 提升了，但 answer correctness 仍是 0.4375？

**回答：**

检索 benchmark 为了隔离 retrieval，没有使用 DeepSeek，而是采用确定性 sentence selector。更好的 chunk 排名不保证简单 sentence selector 能抽取正确句子，特别是同义问题或一段包含多个字段时。

这说明 RAG 是多阶段系统：retrieval、context construction 和 answer generation 需要分别测。不能把 answer correctness 不变解释成 embedding 完全没用，也不能用 LLM 流畅输出掩盖抽取失败。

### 67. 第一次真实 Provider 评估为什么只有 31/36？

**回答：**

第一类问题是缺失 identifier 的问题仍把弱语义 evidence 交给 DeepSeek。虽然模型最终返回了固定拒答，但这违反“证据不足时不调用 LLM”的硬要求，所以增加了 identifier-aware gate。

第二类问题是 metric 太脆弱，只允许连续字符串。例如模型回答 `price is weighted at 40%`，预期是 `Price 40%`，语义正确却判失败。我将 keyword metric 改成允许有限 filler words，同时增加负测试，确保比例互换仍会失败。之后经历 35/36，最终才达到 36/36。

### 68. 如何评估 prompt injection 防护？

**回答：**

Demo pack 中包含带恶意指令的文档，同时保留正常可回答字段。Eval 检查 prompt-injection category 的最终 evidence 中不能包含被标记的 chunk，并验证系统仍能处理合法内容。

当前检测是 regex baseline，所以评估只能证明覆盖的攻击模板有效。未来需要加入编码变体、间接注入、跨 chunk 指令和多语言攻击，并检查模型输出是否泄露 system prompt 或伪造引用。

### 69. Risk、Diff 和 Agent routing 如何评估？

**回答：**

Risk case 检查期望 category 和关键词是否出现在 findings；Diff case 检查指定字段状态和期望值片段；Agent case 检查 trace 中是否出现 `evidence_search_tool`、`risk_rule_check_tool` 或 `cross_doc_diff_tool`。

这是 deterministic contract testing，不是 LLM judge。优点是稳定、免费、适合 CI；不足是无法完整评价解释质量和法律合理性。后续可以增加人工标注和独立 judge，但必须保留可重复 baseline。

### 70. 项目如何做自动化测试和 CI？

**回答：**

后端使用 pytest 覆盖 API、service、RAG、Provider smoke metrics、DOCX、report、风险和 diff；Ruff 做静态检查。前端运行 Next.js typecheck 和 production build。根目录 `scripts/verify_all.py` 串联 backend tests、Ruff、Provider smoke、两套 eval、retrieval benchmark、frontend typecheck 和 build。

GitHub Actions 使用 local deterministic Provider，不需要真实 API Key，分别运行 backend 和 frontend job。PostgreSQL pgvector smoke 当前在本地 Docker 验证，默认 CI 还没有 database service，这是明确的后续工作。

---

## 八、工程化、系统设计与压力追问

### 71. 如果要支持一百万个 chunk，你会怎么改？

**回答：**

首先将上传改成异步 ingestion job，文档存对象存储，worker 批量解析和 embedding；数据库使用 PostgreSQL pgvector，并根据数据分布评估 HNSW 或调优 ivfflat，而不是在 Python 中加载全部 chunk。查询必须按 tenant、document、language 等 metadata 先过滤，再向量检索。

还需要 embedding batch、幂等任务、失败重试、索引维护、连接池、缓存和监控。评估集要按真实流量分层，因为一百万 chunk 下延迟和 hard negative 数量都会变化。

### 72. 如果部署为商业产品，最缺什么？

**回答：**

最缺的不是更多页面，而是安全和数据质量：认证授权、租户隔离、加密、审计策略、病毒扫描、文件大小限制、对象存储、异步任务、OCR/layout parsing、人工复核、数据保留政策、可观测性和真实法律语料评估。

此外风险规则需要领域专家验证，输出免责声明不能替代合规设计。当前项目是 portfolio release candidate，不是商业法律 SaaS。

### 73. 如何保护用户合同和 API Key？

**回答：**

当前本地模式将文件和数据库保存在用户机器，`.env` 和 uploads 被 Git 忽略；真实 Key 不进入日志、测试和文档。公开服务需要 TLS、secret manager、磁盘与备份加密、对象级访问控制、最小权限数据库账号、日志脱敏和删除策略。

还要明确第三方模型的数据处理政策。高敏合同可以部署本地 embedding 与本地 LLM，或在调用云模型前做字段脱敏。不能只说“用了 HTTPS 所以安全”。

### 74. 如何改进中文招投标文档支持？

**回答：**

当前 tokenizer、stopwords、领域短语和 regex 主要针对英文 demo。中文版本要使用中文分词或直接采用 multilingual tokenizer-aware chunking，扩展中文字段标签、日期金额解析、采购术语和 prompt injection 模式，并选择经过中文检索验证的 embedding。

最重要的是引入公开、非机密的中文招标文件和人工标注 page/chunk，而不是只翻译合成数据。所有权重和阈值需要重新跑 benchmark。

### 75. 为什么没有做 OCR？

**回答：**

OCR 会引入模型体积、版面恢复、表格、坐标映射和质量评估等完整子系统。如果只“接一个 OCR API”却没有 OCR confidence、错误样本和页坐标验证，会扩大项目范围但不增加可信度。

当前先把 born-digital PDF 的 RAG、Provider、pgvector 和 eval 做扎实。未来 OCR 应作为独立 pipeline：页面渲染、文本块和 bbox、语言检测、质量阈值、人工纠正，再与 citation viewer 对齐。

### 76. 如何优化延迟？

**回答：**

先通过 trace 分解解析、embedding、vector query 和 LLM latency。上传阶段做 batch embedding 和异步任务；查询阶段缓存重复 query embedding，限制 top-k 和 context 长度，使用连接池并选择合适 vector index。LLM 可以启用 provider cache、流式响应和更小模型。

不能只优化 FastAPI handler，因为真实实验中 LLM aggregate latency 约 29.6 秒，embedding 约 3.9 秒，主要瓶颈在 Provider 调用。

### 77. 项目看起来不复杂，是不是只是把几个 API 拼起来？

**回答：**

界面流程确实保持简单，这是有意的。复杂度集中在可信边界：双数据库路径、真实 Provider、pgvector、hybrid ranking、版本 hard negative、identifier gate、prompt injection filtering、tool trace 和分阶段 eval。

我不会用页面数量证明技术深度，而是展示真实失败如何被测试发现、修复后指标如何变化，以及哪些问题仍未解决。相比堆多 Agent 或 OCR，这些工作更能证明 AI 应用工程能力。

### 78. 这个项目中最有价值的 bug 修复是什么？

**回答：**

最有价值的是 missing identifier gate。问题问 vendor tax ID 时，语义检索可能找到供应商 chunk，模型也可能最终拒答，但弱 evidence 已经进入 LLM。这个行为不符合“证据不足跳过 LLM”的设计。

我将问题分类为 identifier query，再要求 evidence 中存在明确标签和值，排除 missing、unknown 等占位文本。修复后 API 返回 exact fallback、evidence 为空、LLM skipped，并加入回归案例。这个例子能说明我不是只检查最终字符串，而是检查整个信任边界。

### 79. 如果继续做一个最高投入产出比的改进，你选什么？

**回答：**

我会先加入 30 到 50 条公开中文 tender 的人工 page/chunk 标签，并针对现有 5 个 hard miss 比较 query/document prefix、query expansion 和 reranker。只有新方法在 Recall@k、MRR、延迟和成本上有明确收益才保留。

其次是把 PostgreSQL pgvector 加入 CI integration service。它比增加更多前端页面更能提高项目可信度。

### 80. 你如何总结这个项目体现的能力？

**回答：**

它体现的是端到端 AI 应用工程：不仅会调用模型，还能设计文档 ingestion、数据库 schema、检索、证据门控、工具编排、前端证据展示、评估、失败分析、成本观测和 CI。

我最希望面试官记住两点：第一，系统证据不足时确实不会调用 LLM；第二，我用真实 benchmark 证明语义检索有提升，也诚实保留 Recall@5 `0.6875` 和五个失败案例。

---

## 九、面试官可能继续追问的快速回答

| 追问 | 建议回答 |
| --- | --- |
| 为什么不用 Elasticsearch？ | 当前语料和项目规模下 PostgreSQL 同时承担业务数据和 vector search 更简单；数据量和复杂全文检索需求增加后，再用 benchmark 比较 Elasticsearch/OpenSearch。 |
| 为什么不用 LangChain？ | 核心链路很短，直接 service 更透明、更易测试；需要大量 connector 或复杂 chain 时再引入。 |
| 为什么不是纯向量检索？ | 日期、金额和字段标签适合精确关键词；hybrid 在 hard negative 场景更稳。 |
| 为什么 top-k 默认较小？ | 限制 LLM context 噪声和成本；k 应通过 recall/latency 实验调整。 |
| 如何避免重复文档？ | 当前没有 content hash 去重；生产版会保存 SHA-256、source version 和 idempotency key。 |
| 文件很大怎么办？ | 当前一次性读取，生产版应设置大小上限、流式保存、异步解析和分页 batch embedding。 |
| 支持表格吗？ | schema 预留 `document_tables`，但当前没有完整表格抽取，不能声称已实现。 |
| 支持 PDF 高亮吗？ | 当前是 chunk-level navigation，不是 bbox 级像素高亮。 |
| 如何删除文档？ | 当前 MVP 没有删除 API；生产版需级联删除 chunks、vectors、findings、object storage 和审计记录。 |
| 为什么报告是 Markdown？ | 依赖小、可审计、适合 GitHub demo；正式产品可在同一结构化数据上生成 PDF/DOCX。 |
| Provider 换模型要注意什么？ | dimension、query/document encoding、成本、timeout、response schema和回归指标，不能只换 model name。 |
| pgvector index 一定生效吗？ | 小数据集 planner 可能顺序扫描；需用 EXPLAIN ANALYZE 和真实规模验证，而不是只看 index 已创建。 |
| ivfflat 的问题是什么？ | 需要合适 lists/probes 和足够数据，索引召回与速度有权衡；当前只验证路径，不声称完成生产调优。 |
| 如何评估 faithfulness？ | 当前主要靠固定证据、关键词和人工可查 citation；下一步可做逐句 evidence entailment 和人工抽检。 |
| 会保存用户聊天记录吗？ | 当前保存 Agent runs 和 tool calls，不是完整多轮聊天产品。 |
| 有用户权限吗？ | 没有，项目明确不做多租户 SaaS；公开部署前必须补认证授权和隔离。 |

---

## 十、不能说错的边界

- 不要说“系统准确率 100%”；应说 36 条工作流回归通过，独立检索 Recall@5 为 `0.6875`。
- 不要说“风险检查等于法律审查”；它是确定性采购风险信号。
- 不要说“支持扫描 PDF”；当前没有 OCR。
- 不要说“支持 PDF 精确高亮”；当前只有 page/chunk navigation。
- 不要说“DOCX 支持真实页码和修订”；当前只提取 Word XML 段落并记为 page 1。
- 不要说“local hash 是语义 embedding”；它是无 Key、确定性的测试 fallback。
- 不要说“pgvector 让检索自动变准”；它提供数据库向量路径，质量主要取决于 embedding、候选和 ranking。
- 不要说“prompt injection 已完全解决”；当前是 regex baseline。
- 不要说“这是生产级商业合同系统”；它是经过真实 Provider 和评估验证的 portfolio release candidate。

## 面试前最后检查

- 能在白板上画出 ingestion 和 query 两条数据流。
- 能解释 60/40 hybrid score、`0.55` semantic threshold 和 identifier gate。
- 能说清 `36/36` 与 `Recall@5=0.6875` 为什么不矛盾。
- 能复述至少两个真实失败和对应修复。
- 能现场打开 Q&A evidence card、document chunk 和 Agent Trace。
- 能说明没有做 OCR、复杂权限和多 Agent 的原因。
- 能用一句话总结：**BidGuard AI 的重点不是让 LLM 多回答，而是知道什么时候可以回答、依据是什么，以及哪里仍然会失败。**
