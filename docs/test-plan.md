# Test Plan — 测试策略

> Sponge 的测试策略遵循"每一分钱都要花在刀刃上"的原则——测试应该**快**（CI 不能成为开发瓶颈）、**省**（永远不浪费真实 LLM 调用）、**有洞察**（基准测试必须验证省钱效果）。

---

## 测试分层

```
         ┌──────────────────────────────┐
         │     Benchmark / E2E Tests     │  ← 慢、贵、洞察力强
         │  (cost-per-task, savings ratio)│
         ├──────────────────────────────┤
         │     Integration Tests         │  ← mock LLM, 测试管线
         │  (cache, compression, plugins)│
         ├──────────────────────────────┤
         │        Unit Tests             │  ← 快、密集、覆盖核心逻辑
         │  (math, models, token counting)│
         └──────────────────────────────┘
```

---

## 第 1 层：单元测试

**目标：** 覆盖所有纯逻辑，不涉及 LLM 调用或外部资源。

**运行命令：** `pytest tests/unit/ -v`

**覆盖范围：**

| 模块 | 测试内容 | 数量目标 |
|------|---------|---------|
| `cost/models.py` | CostEntry/CostSummary 计算、序列化/反序列化 | ≥ 10 |
| `cost/tracker.py` | 累加逻辑、多 session 聚合、边界条件 | ≥ 15 |
| `cost/estimator.py` | tiktoken 计数、定价表查找、估算 vs 实际偏差 | ≥ 15 |
| `cost/budget.py` | 三轴检查（per-call/cumulative/steps）、边界值、溢出 | ≥ 15 |
| `cache/base.py` | Cache ABC 一致性、TTL 检查、键冲突 | ≥ 10 |
| `cache/result_cache.py` | SHA256 键生成、命中/未命中、TTL 过期 | ≥ 12 |
| `cache/semantic_cache.py` | 余弦距离计算、阈值判断、embedding 缓存 | ≥ 10 |
| `cache/disk_store.py` | SQLite 读写、并发、崩溃恢复 | ≥ 10 |
| `config/settings.py` | TOML 加载、环境变量覆盖、类型验证、默认值 | ≥ 10 |
| `config/loader.py` | 配置文件不存在、格式错误、${VAR} 插值 | ≥ 8 |
| `utils/logging.py` | 结构化日志格式、级别过滤 | ≥ 5 |
| `utils/errors.py` | 异常层级、错误消息格式化 | ≥ 5 |
| `utils/retry.py` | 重试逻辑、退避算法、最大尝试次数 | ≥ 8 |
| `memory/base.py` | MemoryStore CRUD、冲突解决 | ≥ 10 |
| `approval/base.py` | 三梯级检查、配置合并、session 覆盖优先级 | ≥ 15 |
| `telemetry/models.py` | TelemetryEntry/TuningProposal 数据结构 | ≥ 8 |
| `telemetry/feedback.py` | Mann-Whitney U 实现、统计显著性判定 | ≥ 12 |

**关键原则：**
- 不调用 LLM API
- 所有外部依赖（SQLite、文件系统）使用临时目录/mock
- tiktoken 测试用已知字符串验证 token 计数准确性

---

## 第 2 层：集成测试

**目标：** 验证组件之间的交互。LLM 调用全部 mock。

**运行命令：** `pytest tests/integration/ -v`

**覆盖范围：**

### 核心循环

| 测试场景 | 验证点 |
|---------|--------|
| 单轮对话，无工具调用 | 消息传递、响应处理、成本追踪 |
| 多轮对话，有工具调用 | 工具结果追加、循环终止条件 |
| 流式输出渲染 | ContentDelta 逐个发送、ToolCallEvent 正确触发 |
| 审批门集成 | Allow → 自动执行、Confirm → 回调等待、Reject → 跳过 |
| 记忆注入 | .sponge/memory.toml 内容出现在 system prompt 中 |

### 上下文压缩管线

| 测试场景 | 验证点 |
|---------|--------|
| L2 观测屏蔽 | 超过 masking_threshold 的工具输出被替换为占位符 |
| L3 消息修剪 | 超过 min_turns 的对话轮数被裁剪 |
| L4 LLM 总结 | 超过 summarize_after_turns 时触发外部总结调用 |
| L5 滑动窗口 | 消息列表不超过 context window |
| 全管线集成 | 压缩比 ≥ 1.5x（断言要求） |
| 语义保留 | 压缩后的上下文仍然产生正确答案（使用已知测试 prompt） |

### 缓存系统

| 测试场景 | 验证点 |
|---------|--------|
| 精确匹配缓存 | 相同输入 → 缓存命中 → 零成本返回 |
| 语义缓存 | 相似输入（cosine ≥ 0.95）→ 缓存命中 |
| 缓存 + 压缩 | 压缩后的输入仍然匹配原始缓存键 |
| TTL 过期 | 超过 TTL 后缓存失效 → 重新调用 |
| 缓存穿透 | 缓存 miss → 正常调用 → 写入缓存 |

### 插件系统

| 测试场景 | 验证点 |
|---------|--------|
| Native 插件路由 | file_ops 匹配 → 本地执行 → 零成本记录 |
| MCP Server 插件 | MCP server 启动 → 工具发现 → 工具调用 → 结果返回 |
| Server 崩溃恢复 | MCP 子进程崩溃 → 自动重启（最多 3 次） |
| 路由优先级 | Native > MCP > LLM 回退 |
| 审批门 MCP 集成 | MCP 工具经过审批链检查 |

### Session 系统

| 测试场景 | 验证点 |
|---------|--------|
| Session 保存/恢复 | 消息历史、成本状态、上下文状态一致 |
| 崩溃恢复 | event stream 回放恢复状态 |
| 多 session 隔离 | 不同 session 的数据不相互污染 |

### 自调优系统

| 测试场景 | 验证点 |
|---------|--------|
| 遥测收集 | 每次 LLM 调用/缓存决策/压缩事件记录到 SQLite |
| 模式分析 | 请求间隔分析 → 正确 TTL 提案 |
| A/B 测试 | Shadow session 正确打标、成本分别追踪 |
| 调优采纳 | 统计显著的变更正确写入配置 |
| 反馈回路 | 未通过的变更被丢弃，不产生副作用 |

### Mock 策略

```python
# tests/integration/conftest.py

@pytest.fixture
def mock_llm_provider():
    """返回一个模拟的 LLM provider，返回预设的流式事件。"""
    ...

@pytest.fixture
def mock_mcp_server():
    """启动一个假的 MCP server 用于测试。"""
    ...

@pytest.fixture
def temp_sqlite():
    """临时 SQLite 数据库。"""
    ...

@pytest.fixture
def temp_config():
    """临时配置文件。"""
    ...
```

**永远不发出真实 LLM 调用。** 所有测试使用 `mock_llm_provider`。基准测试除外。

---

## 第 3 层：基准测试

**目标：** 验证 Sponge 的省钱效果。这些测试产生真实 API 成本（但控制在每天 $1 以内）。

**运行命令：** `pytest tests/benchmark/ --benchmark`

**注意：** 基准测试需要有效的 API key。不在 CI 中自动运行——按需或 schedule 触发。

### 内部基准

| 测试 | 方法 | 验证点 |
|------|------|--------|
| **压缩节省** | 同一个 prompt 分别用原始上下文和压缩上下文调用，对比 token 消耗与答案所需事实 | token 消耗下降，且 fixture preservation 通过 |
| **缓存节省** | 相同兼容请求连续调用 2 次，对比第 1 次和第 2 次的成本 | 第 2 次没有最终模型调用 |
| **插件节省** | file_ops 任务走插件路径 vs 走 LLM 路径的成本对比 | 插件路径 = $0 |
| **子 agent 节省** | helper agent 探索 → 浓缩 vs 全量直接发给最终模型的成本对比 | ledger 记录 raw exploration、helper cost、summary token 和来源 |

### 竞品对比基准

| 对比对象 | 测试任务 | 指标 |
|---------|---------|------|
| **Claude Code** | 相同的 5 个任务（代码审查、文件编辑、搜索、解释、重构） | 成本/任务、延迟/任务、成功率 |
| **Naive same-model** | 无缓存、无压缩、无插件的直接 API 调用 | Sponge 成本、延迟、成功率与 naive baseline 对比 |
| **Alternative model baseline** | 可选：用户明确选择的较便宜模型 | 仅作参考，不作为 Sponge 核心承诺 |

**基准断言：**

```python
# tests/benchmark/test_savings.py

def test_sponge_beats_naive_opus(benchmark_fixtures):
    """Sponge reports measured savings against the naive same-model baseline."""
    sponge = run_sponge("refactor this module", model="configured")
    naive = run_naive_same_model("refactor this module", model="configured")

    assert sponge.cost <= naive.cost
    assert sponge.quality_checks_passed
    assert sponge.ledger.has_savings_breakdown()

def test_exact_cache_repeat_has_zero_model_spend(benchmark_fixtures):
    """Compatible exact repeats return without a final model call."""
    first = run_sponge("explain this module", model="configured")
    second = run_sponge("explain this module", model="configured")

    assert first.final_model_calls == 1
    assert second.final_model_calls == 0
    assert second.model_spend == 0
```

**成本警示：** 如果基准测试失败且 savings_ratio 恶化，CI 会发送通知。

---

## 目录结构

```
tests/
├── conftest.py                    # 全局 fixtures
├── unit/                          # 第 1 层
│   ├── test_cost_models.py
│   ├── test_cost_tracker.py
│   ├── test_cost_estimator.py
│   ├── test_budget.py
│   ├── test_cache_base.py
│   ├── test_cache_result.py
│   ├── test_cache_semantic.py
│   ├── test_cache_disk_store.py
│   ├── test_config_settings.py
│   ├── test_config_loader.py
│   ├── test_utils_logging.py
│   ├── test_utils_errors.py
│   ├── test_utils_retry.py
│   ├── test_memory_base.py
│   ├── test_approval_chain.py
│   └── test_telemetry_feedback.py
├── integration/                   # 第 2 层
│   ├── conftest.py                # mock LLM provider, temp dirs
│   ├── test_core_loop.py
│   ├── test_streaming.py
│   ├── test_approval_integration.py
│   ├── test_memory_injection.py
│   ├── test_context_pipeline.py
│   ├── test_compression_layers.py
│   ├── test_cache_integration.py
│   ├── test_plugins_native.py
│   ├── test_plugins_mcp.py
│   ├── test_session_save_resume.py
│   ├── test_telemetry_collector.py
│   └── test_self_tuning_loop.py
└── benchmark/                     # 第 3 层（需要 API key）
    ├── conftest.py
    ├── test_compression_savings.py
    ├── test_cache_savings.py
    ├── test_plugin_savings.py
    ├── test_vs_naive_opus.py
    └── test_vs_competitors.py
```

---

## CI 配置（GitHub Actions）

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"
      - run: ruff check src/
      - run: ruff format --check src/
      - run: mypy src/ --strict

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "${{ matrix.python-version }}" }
      - run: pip install -e ".[dev]"
      - run: pytest tests/unit/ -v --cov=src/sponge
      - run: pytest tests/integration/ -v --cov=src/sponge --cov-append
      - run: pytest tests/benchmark/ -v --benchmark    # 仅在 schedule 触发时运行

  benchmark:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[all]"
      - run: pytest tests/benchmark/ -v --benchmark --junitxml=benchmark.xml
      - uses: actions/upload-artifact@v4
        with:
          name: benchmark-results
          path: benchmark.xml
```

**CI 原则：**
- Lint + unit + integration 在每次 push 时运行（< 5 分钟）
- 基准测试按 schedule（每日或每 PR merge）运行
- CI 不消耗真实 LLM 成本（基准测试除外，且有预算上限）

---

## 测试数据管理

| 数据类型 | 位置 | 管理策略 |
|---------|------|---------|
| 测试用 mock 响应 | `tests/fixtures/responses/` | 版本控制 |
| 测试配置文件 | `tests/fixtures/configs/` | 版本控制 |
| 测试项目记忆 | `tests/fixtures/memories/` | 版本控制 |
| 基准测试结果 | 本地生成，不上传 | CI 中 artifact |
| 遥测数据库 | 临时目录，测试后清理 | 每次测试重建 |

---

## 代码覆盖率目标

| 层级 | 覆盖率目标 | 豁免 |
|------|-----------|------|
| 单元测试 | ≥ 90% | __init__.py, 异常类 |
| 集成测试 | ≥ 70% | CLI 入口点（需要交互） |
| 总项目 | ≥ 80% | |

覆盖率虽好，但**不追求 100%**——"savings vs naive" 断言比 100% 行覆盖率更能防止回归。
