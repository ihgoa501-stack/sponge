# Configuration Reference

> Sponge 的配置系统基于 TOML 文件 + 环境变量覆盖。配置文件路径默认为 `~/.sponge/config.toml`，可通过 `SPONGE_CONFIG` 环境变量或 `--config` 参数覆盖。

---

## 配置文件位置

| 层级 | 路径 | 用途 | 自动创建 |
|------|------|------|---------|
| 系统 | `~/.sponge/config.toml` | 全局配置 | `sponge config init` |
| 环境变量 | `SPONGE_*` | 敏感值/部署覆盖 | — |
| 项目 | `<project>/.sponge/memory.toml` | 项目级规则和约定 | 首次写入时 |

**优先级：** 项目 > 环境变量 > 配置文件。环境变量以 `SPONGE_` 为前缀，点号替换为双下划线（如 `SPONGE_BUDGET_CEILING="P75"`）。

---

## 完整配置模板

```toml
# ============================================================================
# Sponge 配置 — ~/.sponge/config.toml
# ============================================================================

# ── 模型设置 ──────────────────────────────────────────────────────────────
[model]
# 主模型标识符。格式: "provider/model-name"
# 支持的 provider: anthropic, openai, deepseek
# 示例: "claude-opus-4-7", "openai/gpt-5.5", "deepseek/deepseek-chat"
default = "claude-opus-4-7"

# 子 agent 使用的模型（通常比主模型便宜）
subagent = "deepseek/deepseek-chat"

# 预处理器使用的模型（本地模型，必须可通过 Ollama 访问）
preprocessor = "ollama/llama-3.2-3b"

# ── Budget ─────────────────────────────────────────────────────────────────
[budget]
# 单次 session 的预算上限。可选值:
# - "P95": 历史分布的 95 分位
# - "P75": 历史分布的 75 分位
# - "P50": 历史分布的 50 分位
# - "$5.00": 固定 5 美元上限
ceiling = "P95"

# 单次 LLM 调用的成本上限（美元）
per_call = 2.00

# 最大工具调用步数
max_steps = 50

# ── 缓存 ───────────────────────────────────────────────────────────────────
[cache]
# 精确匹配结果缓存的 TTL（小时）
result_ttl = 24

# 语义缓存的 TTL（小时）
semantic_ttl = 48

# 语义匹配的余弦相似度阈值（0.0-1.0，越高越严格）
semantic_threshold = 0.95

# 语义缓存使用的 embedding 模型
# 选择后请谨慎变更——切换模型会导致全量缓存失效
embedding_model = "openai/text-embedding-3-small"

# 提示缓存 TTL（分钟或小时）
# 可选值: "5m", "1h"
prompt_cache_ttl = "5m"

# ── 上下文压缩 ────────────────────────────────────────────────────────────
[compression]
# L2 观测屏蔽的触发阈值（token 数）
# 工具输出超过此数量的 token 时才被屏蔽
masking_threshold = 2000

# L3 消息修剪的最小保留轮数
min_turns = 5

# L4 LLM 总结的触发条件：对话轮数 >= 此值时尝试总结
summarize_after_turns = 10

# L4 摘要的目标 token 数
summary_target_tokens = 300

# ── 插件 ───────────────────────────────────────────────────────────────────
[plugins]
# 插件的搜索路径（除了内置插件和 MCP）
# 示例: ["~/.sponge/plugins/", "/usr/local/share/sponge/plugins/"]
extra_paths = []

# ── 审批 ───────────────────────────────────────────────────────────────────
[approval]
# 默认审批策略
# 可选值: "default"（三梯级）, "permissive"（偏向 Allow）, "strict"（偏向 Confirm）
policy = "default"

# 审批覆盖规则
[approval.overrides]
# 格式: "plugin_name.tool_name" = "allow|confirm|reject"
"builtins.file_ops.write_file" = "confirm"
"builtins.shell.exec" = "confirm"

# ── MCP Server ────────────────────────────────────────────────────────────
[mcp.servers]

[mcp.servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]

# 可选的每个工具的审批覆盖
[mcp.servers.filesystem.approval]
write_file = "confirm"
delete_file = "reject"

[mcp.servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
# 环境变量在启动时注入
# ${VAR} 语法从 shell 环境变量中读取
env = { GITHUB_TOKEN = "${GITHUB_TOKEN}" }

# 远程 MCP 服务器（SSE 协议）
# [mcp.servers.remote-api]
# transport = "sse"
# url = "https://api.example.com/mcp"

# ── 沙箱 ───────────────────────────────────────────────────────────────────
[sandbox]
# 默认沙箱类型
# 可选值: "subprocess"（开发用）, "docker", "e2b"
default = "subprocess"

# Docker 沙箱配置（当 sandbox = "docker" 时）
[sandbox.docker]
image = "sponge-sandbox:latest"
network_disabled = false
memory_limit = "2g"
timeout = 300

# E2B 沙箱配置（当 sandbox = "e2b" 时）
[sandbox.e2b]
# template_id = "your-template-id"
# api_key = "${E2B_API_KEY}"

# ── 遥测 ───────────────────────────────────────────────────────────────────
[telemetry]
# 启用遥测收集
enabled = true

# 遥测数据库路径
db_path = "~/.sponge/telemetry/events.db"

# 自调优的 A/B 测试 shadow session 比例（0.0-1.0）
shadow_ratio = 0.20

# 每个参数的测试窗口（session 数）
test_window = 20

# ── CLI ────────────────────────────────────────────────────────────────────
[cli]
# 默认输出格式
# 可选值: "auto"（交互式用 rich，管道用 plain）, "plain", "json"
format = "auto"

# 是否默认流式输出
stream = true

# 日志级别
# 可选值: "DEBUG", "INFO", "WARNING", "ERROR"
log_level = "INFO"
```

---

## 环境变量速查

| 环境变量 | 对应配置路径 | 说明 |
|---------|-------------|------|
| `SPONGE_MODEL__DEFAULT` | `model.default` | 主模型 |
| `SPONGE_MODEL__SUBAGENT` | `model.subagent` | 子 agent 模型 |
| `SPONGE_BUDGET__CEILING` | `budget.ceiling` | 预算上限 |
| `SPONGE_BUDGET__PER_CALL` | `budget.per_call` | 单次调用上限 |
| `SPONGE_CACHE__RESULT_TTL` | `cache.result_ttl` | 结果缓存 TTL |
| `SPONGE_CACHE__EMBEDDING_MODEL` | `cache.embedding_model` | Embedding 模型 |
| `SPONGE_CACHE__PROMPT_CACHE_TTL` | `cache.prompt_cache_ttl` | 提示缓存 TTL |
| `SPONGE_COMPRESSION__MASKING_THRESHOLD` | `compression.masking_threshold` | 屏蔽阈值 |
| `SPONGE_COMPRESSION__MIN_TURNS` | `compression.min_turns` | 最小保留轮数 |
| `SPONGE_APPROVAL__POLICY` | `approval.policy` | 审批策略 |
| `SPONGE_SANDBOX__DEFAULT` | `sandbox.default` | 沙箱类型 |
| `SPONGE_TELEMETRY__ENABLED` | `telemetry.enabled` | 遥测开关 |
| `SPONGE_CLI__STREAM` | `cli.stream` | 流式输出开关 |
| `SPONGE_CLI__LOG_LEVEL` | `cli.log_level` | 日志级别 |

环境变量的键名使用双下划线 `__` 分隔嵌套层级。例如 `model.default` → `SPONGE_MODEL__DEFAULT`。

---

## 各 provider 的模型标识符

| Provider | 模型标识符 | 备注 |
|----------|-----------|------|
| Anthropic | `claude-opus-4-7` | 主推 |
| Anthropic | `claude-sonnet-4-6` | 仅子 agent |
| Anthropic | `claude-haiku-4-5` | 仅子 agent |
| OpenAI | `openai/gpt-5.5` | 主推 |
| OpenAI | `openai/gpt-4.7` | 次选 |
| OpenAI | `openai/gpt-4.1-mini` | 仅子 agent |
| DeepSeek | `deepseek/deepseek-chat` | 子 agent 默认 |
| DeepSeek | `deepseek/deepseek-reasoner` | 推理场景 |
| Ollama (本地) | `ollama/<model-name>` | 仅预处理器 |
