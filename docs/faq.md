# FAQ — 常见问题

---

## 项目定位

### Sponge 和 Claude Code 是什么关系？竞争对手？

既是也不是。Sponge 借鉴了 Claude Code 的架构（~30 行核心循环、sub-agent 模式、event stream），但核心差异在于**成本哲学**：

- Claude Code 省钱靠用户手动选 `/effort` 或换模型（slider → cheaper model）
- Sponge 省钱靠基础设施压缩（缓存 + 压缩 + 插件路由），**最终推理模型不静默降级**

Sponge 的目标是：在同一个已配置的最终推理模型上，尽量少重复支付无价值 token。它不是承诺每个任务都更便宜，而是让重复项目、稳定上下文、多轮工作流里的 paid-token footprint 可测量地下行。

### Sponge 和 LangChain / CrewAI 是什么关系？

不同层级。LangChain 是 **Framework**（抽象 + 集成层），CrewAI 是 multi-agent 编排框架。Sponge 是 **Harness**（意见明确的、开箱即用的代理执行环境）。Sponge 不使用 LangChain——直接调用 provider SDK 以减少抽象开销。

### Sponge 和 Reasonix 是什么关系？

Reasonix 也是缓存优先的设计，但它固定在 DeepSeek 生态。Sponge 的边界不同：最终推理模型由用户配置，成本优化发生在上下文、缓存、工具、预处理和审计层。

### 这和 Cursor / Copilot 的"agent mode"有什么区别？

Cursor 和 Copilot 是 IDE 插件——它们的 agent 是编辑器功能的延伸。Sponge 是独立 CLI 工具，不绑定 IDE。你可以把 Sponge 集成到任何工作流（终端、CI/CD、编辑器插件）。

---

## 使用

### 什么时候能用？

当前处于 **Phase 0 foundation** 阶段：仓库骨架和规划文档存在，但 agent runtime 还没实现。预计 Phase 1 完成后（核心循环 + LLM 调用）可以跑基本任务。查看 [project-plan.md](project-plan.md) 了解执行顺序，查看 [ROADMAP.md](../ROADMAP.md) 了解历史清单。

### 需要什么 API key？

至少需要一个 LLM provider 的 API key。推荐配置：

```bash
# Anthropic（主推）
export ANTHROPIC_API_KEY="sk-ant-..."

# 或 OpenAI
export OPENAI_API_KEY="sk-..."
```

DeepSeek 可选（用于子 agent）。Ollama 可选（用于本地预处理）。

### 支持本地模型吗？

支持，但定位为**辅助执行器**（prompt 压缩、草稿生成、检索、验证），不静默替换最终推理模型。最终推理模型由用户配置；如果用户想用本地模型做最终推理，需要显式配置。

### 需要 GPU 吗？

不需要。所有本地处理（token counting、embedding、预处理器）在 CPU 上运行。预处理器使用 Ollama（可选），有 GPU 会更快但不是必需。

---

## 成本

### Sponge 真的能省钱吗？

这是设计目标，但必须按工作负载证明。Sponge 最适合重复项目、稳定系统提示、多轮上下文和可复用搜索结果；一次性任务或频繁变化的代码状态不一定省钱。

| 层 | 节省场景 | 证明方式 |
|------|---------|------|
| 精确缓存 | 相同任务 + 兼容状态 → 零模型调用 | 第二次运行实际 model spend 为 `$0` |
| Prompt cache | 稳定 system prompt / tool schema | provider 账单事件和 savings ledger |
| 压缩 | 多轮对话、长工具输出 | fixture 中 pre/post token 下降且保留答案所需信息 |
| 插件路由 | 读文件、搜索、shell 等本地任务 | ledger 记录 zero-model-cost tool path |
| Helper agent 浓缩 | 大范围探索任务 | 原始探索 token 与返回摘要 token 对比 |
| 自调优 | 有足够历史 fingerprint 后 | replay 先证明，再进入 live shadow |

公开百分比必须等 benchmark 支持。发布前的默认表述是：Sponge 追求同一最终模型下更低的 paid-token footprint，而不是承诺固定节省比例。

### 自调优真的能"越用越便宜"吗？

这是目标，不是早期承诺。自调优需要足够多的 cost fingerprint，并且必须先通过 replay-based optimizer 证明候选配置有净收益。前期不会承诺“每 session 下降 2-5%”。详见 [risk-assessment.md](risk-assessment.md) 的冷启动、小样本和质量风险章节。

### 如果预算超了会怎样？

Circuit breaker 会阻断进一步调用，但**不会把最终推理模型静默换成便宜模型**。预算是风险控制，不是 savings source：它能防止 runaway spend，但不会让一个已经成功完成的相同任务天然更便宜。详见 [security.md](security.md) 的预算章节。

---

## 技术

### 为什么用 Python 不用 TypeScript？

Python 是 AI 生态的母语——Anthropic、OpenAI、tiktoken 的官方 SDK 都是 Python。TypeScript 版往往是社区维护的二级公民。详见 [decisions.md](decisions.md) ADR-007。

### 性能够吗？Python 不是慢吗？

LLM 调用是瓶颈（1-10s），不是 Python 运行时。Sponge 的 CPU 密集型操作只有 token counting（tiktoken 是 C 扩展）和 embedding 计算。异步 IO（asyncio）对 IO 密集型工作负载足够。详见 ADR-007 的后果分析。

### 支持流式输出吗？

是的。流式是默认模式——字符在生成时实时显示，不需要等完整响应。非交互环境用 `--no-stream`。详见 [streaming.md](streaming.md)。

### 支持 MCP 吗？

计划原生支持。`~/.sponge/config.toml` 中配置 MCP server。内置的 file_ops、shell 等高频操作优先走 native plugin，以减少延迟和安全面。详见 [mcp-integration.md](mcp-integration.md)。

### 可以在 CI/CD 中使用吗？

计划支持。`sponge run --no-stream --auto-approve --json` 是目标管道接口，`--read-only` 模式适合安全审查。详见 [cli-reference.md](cli-reference.md)。

### 支持图片/PDF 输入吗？

计划支持（见 [project-plan.md](project-plan.md) 的 Multimodal + Advanced Providers 阶段）。不同 provider 的图片/PDF 能力、缓存计费和降级路径必须显式展示，不能静默假装等价。

---

## 隐私

### 遥测数据会发送到外部吗？

**不会。** 所有遥测数据存储在本地 `~/.sponge/telemetry/events.db`（SQLite）。无服务器、无云依赖、无数据离开机器。详见 [self-tuning.md](self-tuning.md) 的隐私章节。

### Memory 文件（.sponge/memory.toml）包含敏感信息吗？

可能包含项目级规则和约定，通常不包含密钥。密钥通过环境变量注入（`${VAR}` 语法）。但如果你在里面写了敏感信息，它会被注入到 LLM 调用的 system prompt 中——所以**不要在 memory 文件中放密钥**。

### API key 存在哪里？

不存储在 Sponge 配置中。通过环境变量（`ANTHROPIC_API_KEY`、`OPENAI_API_KEY`）注入。Sponge 的配置支持 `${VAR}` 语法引用环境变量，但值写在配置文件中时要注意文件权限。

---

## 开发

### 如何贡献？

详见 [CONTRIBUTING.md](../CONTRIBUTING.md)。简要流程：选一个 Phase → 开 issue → 创建 `phase-N-xxx` 分支 → 写代码 + 测试 → PR。

### 需要写测试吗？

是的。三层测试：单元（纯逻辑）、集成（mock LLM）、基准（真实 API，验证省钱效果）。详见 [test-plan.md](test-plan.md)。

### 测试需要 API key 吗？

单元测试和集成测试不需要（LLM 全部 mock）。基准测试需要，按 schedule 运行。

### 如何报告安全漏洞？

（待定——项目还没公开，安全策略会在发布前建立。）

---

## 路线图

### Phase 0 是什么？

项目基础设施：pyproject.toml、目录结构、CI 配置。让 `pip install -e .` 工作。

### Phase 1 什么时候完成？

没有时间表。这是一个开源项目，进度取决于贡献者。

### 全部 11 个 Phase 都完成需要多久？

不做固定承诺。当前优先级是先完成 Phase 1 的真实成本记录和 Phase 2 的精确缓存 savings proof，再扩展到更大的闭环。

### 我可以跳过一个 Phase 直接开发后面的吗？

不推荐——每个 Phase 依赖前面的基础设施。但 Phase 5（插件系统）之后，Phase 6-11 可以并行开发。
