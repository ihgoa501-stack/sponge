# CLI Reference

> `sponge` 命令的完整参考。所有命令基于 typer 构建，支持 `--help`。

---

## 全局选项

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--version` | flag | — | 打印版本号并退出 |
| `--help` | flag | — | 打印帮助信息 |
| `--config` | path | `~/.sponge/config.toml` | 指定配置文件路径 |
| `--as` | string | — | 切换用户/bot 身份（多账号场景） |
| `--no-stream` | flag | false | 禁用流式输出（CI/管道模式） |
| `--auto-approve` | flag | false | 自动批准所有 Confirm 梯级的工具调用 |
| `--read-only` | flag | false | 拒绝所有写/执行操作（审查模式） |
| `--approval-policy` | string | default | 加载命名审批策略 |
| `--sandbox` | string | subprocess | 沙箱类型：subprocess / docker / e2b |
| `--verbose` | flag | false | 显示详细日志和成本分解 |
| `--json` | flag | false | 以 JSON 格式输出（非交互模式） |

---

## `sponge run` — 执行任务

**用法:** `sponge run [OPTIONS] TASK`

执行一个 AI agent 任务。主要入口点。

### 参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `TASK` | string | ✅ | 任务描述。如 "refactor this file" |

### 选项

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--model` | string | 配置文件中的默认值 | 指定模型，如 `claude-opus-4-7`、`openai/gpt-5.5` |
| `--budget` | float | 配置文件中的上限 | 本次 session 的成本上限（美元） |
| `--max-steps` | int | 50 | 最大工具调用步数 |
| `--image` | path | — | 附加图片（可多次指定） |
| `--file` | path | — | 附加文件（PDF 等，可多次指定） |
| `--memory` | flag | true | 启用项目/用户记忆注入 |
| `--no-cache` | flag | false | 禁用所有缓存（调试用） |
| `--session-id` | string | 自动生成 | 恢复指定 session |

### 示例

```bash
# 基本用法
sponge run "解释 CAP 定理"

# 指定模型和预算
sponge run "重构这个模块" --model claude-opus-4-7 --budget 2.0

# 带截图
sponge run "这个 UI 有什么问题" --image screenshot.png

# 恢复之前的 session
sponge run "" --session-id sess_abc123

# CI 模式（非流式 + 自动批准 + JSON 输出）
sponge run "lint 整个项目" --no-stream --auto-approve --json
```

---

## `sponge session` — 会话管理

**用法:** `sponge session [OPTIONS] COMMAND [ARGS]`

管理会话生命周期。

### 子命令

#### `sponge session start`

启动一个新的交互式 session。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--name` | string | 自动生成 | 会话名称 |
| `--restore` | string | — | 从之前的 session ID 恢复 |

#### `sponge session resume`

恢复一个已保存或中断的 session。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `SESSION_ID` | string | ✅ | 要恢复的 session ID |

#### `sponge session list`

列出所有已保存的 session。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--limit` | int | 20 | 显示最近 N 个 session |
| `--status` | string | — | 过滤：active / completed / interrupted |
| `--json` | flag | false | JSON 格式输出 |

#### `sponge session delete`

删除一个已保存的 session。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `SESSION_ID` | string | ✅ | 要删除的 session ID |

### 示例

```bash
# 启动命名 session
sponge session start --name "big-refactor"

# 恢复中断的 session
sponge session resume sess_abc123

# 查看最近的 session
sponge session list --limit 10

# JSON 格式查看全部活跃 session
sponge session list --status active --json
```

---

## `sponge cost` — 成本查看

**用法:** `sponge cost [OPTIONS] COMMAND [ARGS]`

查看和分析成本数据。

### 子命令

#### `sponge cost --session`

显示当前 session 的成本详情。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--detailed` | flag | false | 显示每步成本分解 |
| `--export` | path | — | 导出为 CSV/JSON |

#### `sponge cost --task`

显示单个任务的成本。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `TASK_ID` | string | — | 任务 ID（默认最近的任务） |

#### `sponge cost --summary`

显示汇总统计。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--period` | string | 7d | 统计周期：1d / 7d / 30d / all |
| `--json` | flag | false | JSON 格式输出 |

### 输出示例

```
$ sponge cost --session
═══════════════════════════════════════════
  Session Cost Report
═══════════════════════════════════════════
  Total cost:           $0.1842
  Tokens in:            12,420
  Tokens out:           2,108
  Cache savings:        $0.0821  (30.8%)
  Compression savings:  $0.0412  (15.5%)
  Plugin savings:       $0.0200  (7.5%)
  ─────────────────────────────────
  Savings vs naive:     $0.1433  (53.8%)
═══════════════════════════════════════════
```

---

## `sponge config` — 配置管理

**用法:** `sponge config [OPTIONS] COMMAND [ARGS]`

查看和修改 Sponge 配置。

### 子命令

#### `sponge config init`

生成默认配置文件。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--path` | path | `~/.sponge/config.toml` | 配置文件路径 |
| `--force` | flag | false | 覆盖已有配置文件 |

#### `sponge config show`

显示当前配置。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--format` | string | toml | 输出格式：toml / json / yaml |

#### `sponge config set`

修改配置项。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `KEY` | string | ✅ | 配置键（如 `model`、`budget_ceiling`） |
| `VALUE` | string | ✅ | 配置值 |

#### `sponge config get`

查看指定配置项。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `KEY` | string | ✅ | 配置键 |

#### `sponge config add-mcp`

添加 MCP server。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `NAME` | string | ✅ | server 名称 |
| `--command` | string | ✅ | 启动命令 |
| `--args` | string | — | 命令参数 |
| `--transport` | string | stdio | stdio / sse / streamable-http |
| `--url` | string | — | SSE 连接的 URL |
| `--env` | string | — | 环境变量 KEY=VAL（可多次指定） |

### 示例

```bash
# 初始化配置
sponge config init

# 查看当前配置
sponge config show

# 修改模型
sponge config set model claude-opus-4-7

# 添加 MCP server
sponge config add-mcp github \
  --command npx \
  --args "-y,@modelcontextprotocol/server-github" \
  --env "GITHUB_TOKEN=${GITHUB_TOKEN}"
```

---

## `sponge tune` — 自调优管理

**用法:** `sponge tune [OPTIONS] COMMAND [ARGS]`

查看和管理自调优系统。

### 子命令

#### `sponge tune --report`

显示自调优报告。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--period` | string | 30d | 报告周期 |
| `--json` | flag | false | JSON 格式输出 |

#### `sponge tune --history`

显示调优历史。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--limit` | int | 20 | 显示最近 N 条记录 |

#### `sponge tune --review`

查看待应用的调优提案（高风险变更需要人工审批）。

### 输出示例

```
$ sponge tune --report
═══════════════════════════════════════════════════════════════
  Sponge Self-Optimization Report
═══════════════════════════════════════════════════════════════
  Sessions analyzed:        247
  Parameters auto-tuned:      3   (2 auto-applied, 1 pending)
  Savings from tuning:    $1.87   (12.1% of total spend)

  ┌─ Recent Changes ─────────────────────────────────────────┐
  │ ✔ prompt_cache_ttl    5m → 1h    +$0.31/session (3 days)  │
  │ ✔ masking_threshold 2000 → 3500  +$0.12/session (1 week)  │
  │ ⏳ budget_ceiling   P95 → P80     -$0.05/session (pending) │
  └──────────────────────────────────────────────────────────┘

  Projected annual savings at current rate: $42.50
═══════════════════════════════════════════════════════════════
```

---

## `sponge memory` — 记忆管理

**用法:** `sponge memory [OPTIONS] COMMAND [ARGS]`

查看和编辑项目/用户记忆。

### 子命令

#### `sponge memory show`

显示当前项目和用户记忆。

| 选项 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `--project` | flag | true | 显示项目记忆 |
| `--user` | flag | false | 显示用户偏好 |
| `--json` | flag | false | JSON 格式输出 |

#### `sponge memory add`

添加一条记忆规则。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `RULE` | string | ✅ | 规则内容，如 "Use httpx not requests" |
| `--key` | string | 自动生成 | 规则键名 |
| `--scope` | string | project | project / user |

#### `sponge memory remove`

删除一条记忆规则。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `KEY` | string | ✅ | 规则键名 |

### 示例

```bash
# 查看项目记忆
sponge memory show

# 添加规则
sponge memory add "Never modify test/fixtures/" --key no_touch

# 删除规则
sponge memory remove no_touch
```

---

## `sponge mcp` — MCP Server 管理

**用法:** `sponge mcp [OPTIONS] COMMAND [ARGS]`

管理 MCP server。

### 子命令

#### `sponge mcp list`

列出已注册的 MCP server。

#### `sponge mcp status`

显示 MCP server 的运行状态。

#### `sponge mcp restart`

重启 MCP server。

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `NAME` | string | ✅ | server 名称 |

#### `sponge mcp add`

添加 MCP server（同 `sponge config add-mcp`）。

---

## `sponge version`

**用法:** `sponge version`

打印版本号和构建信息。

---

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功完成 |
| 1 | 一般错误（配置错误、provider 不可用等） |
| 2 | 预算超限（circuit breaker 阻断） |
| 3 | 用户中断（Ctrl+C） |
| 4 | 审批拒绝（关键操作被拒绝后用户选择退出） |
