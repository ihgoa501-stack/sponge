# Sponge 术语表

> 项目核心概念的准确定义。按字母顺序排列。

---

### A

**Approval Gate（审批门）**
: 工具执行前的权限检查点。每个工具调用通过 Allow（自动执行）/ Confirm（弹窗确认）/ Reject（阻止）三梯级审批链。详见 [security.md](security.md)。

**Agent Harness**
: 相较于 Framework（抽象层）和 Runtime（执行层），Harness 是一个意见明确的、开箱即用的代理执行环境——提供 agent 循环、工具执行、上下文管理、sub-agent 调度、记忆、沙箱和规划基础设施。Sponge 是一个 Harness。

---

### B

**Configured Final Model（已配置最终模型）**
: Sponge 的核心原则。最终推理模型由用户配置，Sponge 不会为了省钱静默替换它。辅助执行器可以更便宜或本地运行，但只负责准备、检索、压缩或验证上下文。

**Budget Ceiling（预算上限）**
: 单次 session 的成本上限。默认可基于历史分布（如 P95），支持 P75、P50、或固定金额。超出时 circuit breaker 阻断进一步调用。预算上限是风险控制，不计入节省来源。

---

### C

**Cache Hit Rate（缓存命中率）**
: 缓存命中的请求占总请求的比例。该指标必须按工作负载解释：重复 Q&A 和稳定项目说明可能很高，活跃 coding task 通常较低。命中 = 零模型调用（exact match）或在状态兼容时复用语义相近结果（semantic match）。

**Circuit Breaker（断路器）**
: 三轴预算检查器：① 单次调用 ≤ 上限 ② 累计 ≤ 预算 ③ 步数 ≤ 上限。超出时停止执行（从不降级模型）。支持阻塞模式（调用前检查）和流模式（流中检查）。

**Condensation（浓缩）**
: Helper/sub-agent 执行结束后，将其完整输出压缩为结构化摘要的过程。最终模型只看到带来源的摘要，不是原始探索日志。压缩倍率必须按任务报告，不能作为通用承诺。

**Content Block（内容块）**
: 消息的组成单元。支持 `text`、`image`、`pdf`、`tool_use`、`tool_result` 类型。参见 [memory.md](memory.md) 的多模态章节。

**Context Compression（上下文压缩）**
: 在每次 LLM 调用前，对消息列表进行缩减以减少 token 消耗的过程。Sponge 使用 5 层管线：服务端清除 → 观测屏蔽 → 消息修剪 → LLM 总结 → 滑动窗口。参见 [context-pipeline.md](context-pipeline.md)。

---

### E

**Event Stream（事件流）**
: 追加只读的事件日志。记录每个 TaskStarted、ToolCall、ApprovalDecision、TaskCompleted。用于审计、调试、崩溃恢复。模式类似 Anthropic Managed Agents。

**Exact Match Cache（精确匹配缓存）**
: 基于 SHA256 全量（task + system prompt + tools）哈希的缓存。完全相同输入的重复请求返回缓存结果，零 token 成本。

---

### F

**Feedback Loop（反馈回路）**
: 自调优系统的验证阶段。候选参数先经过历史 cost fingerprint replay，再进入 shadow 模式 A/B 测试。采纳条件同时检查成本、延迟和质量风险信号。参见 [self-tuning.md](self-tuning.md)。

---

### H

**Harness** → 见 Agent Harness

---

### L

**LLM Provider（LLM 提供商抽象层）**
: 统一的流式接口（`stream()` 方法）包装不同 API 提供商。每个 provider 声明其能力（图片/PDF 支持、服务端清除、缓存定价），管线自适应。参见 [architecture.md](architecture.md)。

---

### M

**MCP（Model Context Protocol）**
: 业界标准 AI 工具协议。Sponge 通过 `MCPServerPlugin` 适配器原生支持 MCP server。内置插件（file_ops、shell）绕过 MCP 直接执行。

**Memory Injection（记忆注入）**
: 在 session 启动时，将 project 级 `.sponge/memory.toml` 和 user 级 `~/.sponge/preferences.toml` 注入到 system prompt 的过程。参见 [memory.md](memory.md)。

**Message Pruning（消息修剪）**
: 上下文压缩的第三层。根据重要性评分（最近 > 旧、错误 > 成功、推理 > 观测）选择保留哪些 turn。始终保留最少 5 个 turn 和第一条用户消息。

**Model Routing（模型路由）**
: Sponge 刻意避免的模式。指根据任务复杂度将请求分配给不同价位模型的做法。Sponge 从不这样做。

---

### O

**Observation Masking（观测屏蔽）**
: 上下文压缩的第二层。将旧的工具输出内容替换为 `[...N tokens omitted...]` 占位符。规则：只屏蔽 tool 和 user 消息，永不屏蔽 assistant 推理内容，保留最近 3 个工具结果。参见 [context-pipeline.md](context-pipeline.md)。

---

### P

**Pattern Analyzer（模式分析器）**
: 自调优系统的第二阶段。运行 SQL 查询聚合遥测事件，检测优化机会。分析的信号：请求间隔、压缩率、预算利用率、任务重复频率。参见 [self-tuning.md](self-tuning.md)。

**Plugin Routing（插件路由）**
: 根据任务描述匹配最适合的插件执行，绕过 LLM 调用。匹配优先级：内置插件（file_ops、shell）→ MCP 工具 → LLM 回退。

**Preprocessor（预处理器）**
: 在 LLM 调用前对 prompt 进行本地处理的模块。使用本地 Ollama 模型压缩长 prompt 或生成草稿。可选、可降级——不可用时直接穿透。

**Prompt Cache（提示缓存）**
: 利用 API 提供商的缓存机制（Anthropic 的 `prompt_cache_retention` 等），对 system prompt、工具定义、历史消息的部分内容进行缓存。缓存命中时，这些 token 只需支付 10%（Anthropic）或 50%（OpenAI）的成本。

**Provider Capabilities（提供商能力声明）**
: 每个 LLM provider 实现声明的能力集：是否支持服务端清除、图片/PDF、缓存折扣率等。管线在运行前查询，跳过不可用的层。参见 ADR-010。

---

### S

**Savings vs Naive（相对于朴素方案的节省）**
: 每个任务/ session 的报告中，对比"Sponge 的实际花费"和"同样的任务用朴素 API 调用（无缓存、无压缩、插件）会花多少钱"的比率。核心指标。

**Semantic Cache（语义缓存）**
: 基于 embedding 余弦相似度的缓存。当输入与已有缓存的输入的语义相似度 ≥ 阈值（默认 0.95）时，返回缓存结果。需要 embedding 模型，存在供应商锁定风险（参见 [risk-assessment.md](risk-assessment.md)）。

**Session（会话）**
: 一次 Sponge 交互的生命周期。从 `sponge run` 开始，到任务完成或用户中止结束。支持 save/resume。参见 [ROADMAP.md](ROADMAP.md) Phase 7。

**Shadow A/B Testing（影子 A/B 测试）**
: 自调优系统的验证方法。20% 的 session 使用新参数值（shadow），80% 使用旧值（baseline），各自独立记录成本。Mann-Whitney U 检验判断新参数是否更好。

**Sub-Agent（子代理）**
: 在隔离上下文中执行的 agent 实例。只接收系统 prompt + 委托消息。执行完毕后返回浓缩结果。不能嵌套子代理。

---

### T

**Telemetry Collector（遥测收集器）**
: 自调优系统的第一阶段。非阻塞地记录每个 cost-significant 事件到 SQLite。异步批量写入，开销 < 0.1ms/事件。参见 [self-tuning.md](self-tuning.md)。

**Token（令牌）**
: LLM 的输入/输出基本单位。Sponge 追踪每个任务、session 的 token 消耗和对应的美元成本。

**Tuning Proposal（调优提案）**
: Pattern Analyzer 的输出。包含参数名、当前值、建议值、理由和预估节省。经过 Feedback Loop 的 A/B 测试后，由 Parameter Tuner 采纳或拒绝。

---

### Z

**Zero-Cost Task（零成本任务）**
: 通过插件路由完全绕过 LLM 的任务。例如文件读取、搜索、shell 命令执行。这些任务的成本 = $0（除了运行插件本身的 CPU/内存）。

---

## 概念关系图

```
┌─────────────────────────────────────────────────────────┐
│                        Session                          │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │  Memory   │  │ Approval │  │   Agent Loop         │ │
│  │  Inject   │  │   Gate   │  │                      │ │
│  │  (start)  │  │ (per op) │  │  stream → match      │ │
│  └─────┬─────┘  └────┬─────┘  │  → execute → repeat  │ │
│        │             │        └──────────┬───────────┘ │
│        ▼             ▼                   ▼              │
│  ┌──────────────────────────────────────────────┐       │
│  │           Cost Infrastructure                 │       │
│  │  ┌────────┐ ┌──────────┐ ┌───────────────┐   │       │
│  │  │ Cache  │ │Compressor│ │ Cost Tracker  │   │       │
│  │  └────────┘ └──────────┘ └───────┬───────┘   │       │
│  └──────────────────────────────────┼───────────┘       │
│                                     ▼                    │
│                          ┌──────────────────┐            │
│                          │   Telemetry      │            │
│                          │   Collector      │            │
│                          └────────┬─────────┘            │
│                                   ▼                      │
│                     (background, end of session)         │
│                    ┌────────────────────────┐            │
│                    │  Self-Tuning Pipeline  │            │
│                    │  Analyze → Test → Apply│            │
│                    └────────────────────────┘            │
└─────────────────────────────────────────────────────────┘
```
