# 风险与取舍 — Risk Assessment

> Sponge 的设计中有许多刻意的取舍。每个选择都有对应的风险。这篇文档不隐藏这些风险——它们不是 bug，是已知的设计权衡。

---

## 1. 自调优冷启动

### 问题

所有自调优参数都从默认值开始。在前 N 个 session 里（N ≈ 10-30，取决于使用频率），没有足够的遥测数据来产生有意义的提案。

| Session 范围 | 遥测数据量 | 分析器行为 | 用户感受 |
|-------------|-----------|-----------|---------|
| 1-10 | < 50 事件 | 数据不足，不产生提案 | 默认参数可能不理想 |
| 11-30 | 50-300 事件 | 开始产生提案，但置信度低 | 部分参数开始调整 |
| 31+ | 300+ 事件 | 稳定产生提案，统计显著 | 系统逐渐收敛到最优 |

### 缓解措施

| 措施 | 效果 |
|------|------|
| **合理默认值** | 所有参数默认值来自 Claude Code、Cursor 等的经验值，不是瞎猜 |
| **保守的冷启动** | 前 10 个 session 分析器不产生提案，只收集数据 |
| **人工预调** | `sponge config set` 允许用户在冷启动期直接覆盖参数 |
| **配置文件模板** | `sponge config init` 生成带注释的默认配置，用户可以预先调整 |
| **渐进式提案** | 早期提案只影响低风险参数（cache TTL → 低成本），高风险提案（budget ceiling → 等到 30+ session） |

### 不可消除的剩余风险

第一个 session 的参数不是最优的。如果你恰好在前 10 个 session 里跑了一个超长任务，默认 budget ceiling 可能偏高或偏低。这是一个没有历史数据的根本限制。

---

## 2. 反馈回路偏离

### 问题

自调优系统可能"学到"错误的东西，进入一个自我强化的次优循环。

### 场景 A：压缩率优化偏差

```
问题： 分析器发现压缩率 < 1.2x → 提高 masking_threshold
      提高后压缩率上升 → 分析器认为"优化有效"
      但实际上过度屏蔽了模型需要的信息 → 回答质量下降但未被检测到
```

**缓解措施：** 分析器只跟踪压缩率，不跟踪回答质量。这是一个已知局限——目前没有自动化的质量评估。缓解方案：

- `sponge tune --review` 显示待应用的变更，用户可以人工判断
- 高风险提案（> $0.50/session 影响）默认需要人工审批
- 回答质量下降最终会表现为用户手动回滚参数（`sponge config set masking_threshold=2000`），telemetry 会记录这个回滚信号

### 场景 B：预算螺旋

```
问题： budget ceiling 从 P95 降到 P75 → 用户觉得太紧 → 用户降低使用频率
      使用频率下降 → 分析器检测到更低的 budget 利用率 → 进一步降低 ceiling
      → 用户完全停止使用
```

**缓解措施：**
- budget ceiling 有硬地板（不低于 P50）
- 用户显式覆盖（`sponge config set budget_ceiling=P95`）触发分析器"暂停此参数 30 天"
- 如果 session 计数骤降（使用频率下降 >50%），分析器暂停所有负面调优（只做膨胀，不做收缩）

### 场景 C：缓存 TTL 策略反转

```
问题： 分析器发现请求间隔中位数 8 分钟 → 把 TTL 从 5m 提到 1h → 缓存命中率上升
       → 分析器认为有效 → 继续提到 4h → 但 cache write 成本也上升了
       → 写入成本开始侵蚀缓存节省
```

**缓解措施：**
- 每个缓存参数有硬上限（`prompt_cache_ttl` 上限 4 小时）
- 反馈回路的 A/B 测试同时检查"总成本"（写 + 读），不只是命中率
- 如果 cache write 成本 > 缓存节省，提案被拒绝

### 不可消除的剩余风险

没有自动化的回答质量评估。自调优系统优化的是**成本指标**（每 session 花费），不是**质量指标**（回答准确率）。如果压缩损害了质量但没有被用户察觉，系统不会自动回滚。这是所有只跟踪成本不跟踪质量的系统的固有限制。

---

## 3. Provider 特性静默失效

### 问题

某些压缩层只对特定 provider 有效。如果用户切换 provider，这些层静默退化。

| 特性 | 生效 Provider | 切换后行为 | 风险等级 |
|------|--------------|-----------|---------|
| L1: Server-side tool result clearing | Anthropic | OpenAI/DeepSeek: 无此 API → Layer 1 不做任何事 | 🔴 高 |
| Prompt cache 10% 读成本 | Anthropic | OpenAI: 50% 读成本 → 缓存节省减半 | 🟡 中 |
| PDF 输入 | Anthropic + OpenAI | DeepSeek: 不支持 PDF → 需要回退到子 agent 提取文本 | 🟡 中 |
| 思考块（thinking blocks） | Anthropic | OpenAI/DeepSeek: 无此概念 | 🟢 低 |

### 缓解措施

**Provider 能力声明：** 每个 provider 实现声明其能力集：

```python
class AnthropicProvider(LLMProvider):
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            server_side_clearing=True,
            prompt_cache_cost_ratio=0.1,  # 10% of input cost
            supports_images=True,
            supports_pdf=True,
            supports_thinking=True,
        )
```

**压缩管线适配：** Context compressor 在运行前检查 provider 能力，跳过不可用的层：

```python
async def compress(self, messages, provider_capabilities):
    layers = [
        Layer1ServerClear if provider_capabilities.server_side_clearing else NoopLayer,
        Layer2Masking,     # provider-agnostic
        Layer3Pruning,     # provider-agnostic
        Layer4Summarize,   # provider-agnostic (uses external cheap model)
        Layer5Slide,       # provider-agnostic
    ]
    for layer in layers:
        messages = await layer.apply(messages)
    return messages
```

**配置警告：** 当用户切换 provider 时，CLI 显示提醒：

```
$ sponge config set model=openai/gpt-5.5
⚠️  Provider change detected: Anthropic → OpenAI
   - Server-side tool clearing: ❌ (Anthropic only)
   - Prompt cache cost: 10% → 50%
   - PDF support: ✅
```

### 不可消除的剩余风险

如果用户在配置中切换 provider 但没有注意警告，某些优化层会静默变为 no-op。系统不会阻止这种配置——它只是记录下来供后续成本分析发现。如果切换后成本异常上升，telemetry 会捕捉到信号。

---

## 4. 跨 Provider 成本估算误差

### 问题

`cost_estimator` 使用 tiktoken 做预估算，但 Anthropic 使用自己的 tokenizer：

| Tokenizer | 与 tiktoken 的差异 | 影响 |
|-----------|-------------------|------|
| `claude_tokenizer` (Anthropic) | 对代码和中文略有不同 | 估算偏差 < 5% |
| `tiktoken` (OpenAI) | 准确 | 无偏差 |
| `tiktoken` (DeepSeek) | 兼容 OpenAI | 无偏差 |

此外，**缓存命中成本在调用前不可预测**——你不知道系统 prompt 是否还在缓存中。

### 缓解措施

- 预估算标注为 "estimated"（不是精确值），实际成本在 UsageEvent 中报告
- 缓存命中率估算：使用过去 N 次的平均命中率作为加权因子
- 输出成本标注为 "unknown until stream ends"——仅在流结束后报告
- 如果预估算与实际成本的偏差 >20%，telemetry 记录一个事件用于后续校准

### 不可消除的剩余风险

调用前的成本估算永远是不精确的。这就是为什么它叫"估算"（estimate），不叫"计价"（invoice）。所有财务决策（circuit breaker 拦截）应该基于实际成本，而不是估算成本。

---

## 5. Embedding 模型供应商锁定

### 问题

Semantic cache 依赖 embedding 模型计算余弦相似度。一旦生产环境积累了数万条缓存记录，更换 embedding 模型会导致**全量缓存失效**——因为新旧 embedding 向量不可比较。

### 场景

```
Phase 1: 使用 OpenAI text-embedding-3-small → 20,000 条缓存记录
Phase 2: 切换到 text-embedding-3-large（更高维度） → 所有缓存 miss
         → 重新填充缓存 → 这段时间内所有请求都要付全价
```

### 缓解措施

| 措施 | 效果 |
|------|------|
| **Embedding 配置锁定** | 首次生成缓存后，配置记录 embedding 模型 ID。切换模型需要显式确认。 |
| **双写迁移** | 在迁移期，新旧 embedding 同时写入（新请求用新模型写，旧缓存用旧模型读）。 |
| **降级策略** | 如果新 embedding 的缓存 miss，回退到 exact-match cache，不产生额外 LLM 成本。 |
| **优先用本地 embedding** | Ollama 的 nomic-embed-text 是免费的，不存在 API 锁定问题。 |

### 推荐策略

首次配置时选择 embedding 模型视为**永久决策**。建议：

1. 开发阶段用 `text-embedding-3-small`（便宜、足够好）
2. 生产环境用 `text-embedding-3-large`（更高精度）——但要确认这是长期选择
3. 敏感/离线场景用 Ollama `nomic-embed-text`（零供应商锁定）

---

## 6. A/B 测试成本

### 问题

自调优系统的 A/B 测试不是免费的。Shadow session 产生的真实 API 费用虽然打上了 shadow 标签，但账单上不会打折。

### 成本估算

| 参数 | 默认 | 每次 A/B 测试的额外成本 |
|------|------|----------------------|
| `prompt_cache_ttl` | 5 min | ~$0.04/session × 4 shadow = $0.16 |
| `masking_threshold` | 2000 | ~$0.02/session × 4 shadow = $0.08 |
| `budget_ceiling` | P95 | ~$0.10/session × 4 shadow = $0.40 |

**如果同时有 3 个活跃实验：** 每 20 个 session 额外花费约 $0.64（假设每个实验 4/20 是 shadow）。

### 保护措施

| 措施 | 说明 |
|------|------|
| **提案频率限制** | 分析器每个参数每 7 天最多产生 1 个提案 |
| **成本门槛** | 提案的预估节省必须 > 预估测试成本的 3 倍 |
| **并行实验上限** | 最多 3 个活跃实验。超过的排队等待。 |
| **低风险快速通道** | <$0.01/session 影响的提案跳过 A/B，直接应用 |
| **实验预算封顶** | 所有实验的测试成本不超过总 API 花费的 5% |

### 不可消除的剩余风险

在重度使用场景（每天 100+ session），即使 5% 的测试预算也是一笔实打实的开销。这个风险只有在 replay 和 live shadow 都证明净收益为正时才可接受；不能预先假设 5% 的测试开销一定换来更高比例的总成本节省。

---

## 7. 统计噪声与小样本

### 问题

A/B 测试的默认设置是 20% shadow / 80% baseline，目标 20 个总 session（4 shadow, 16 baseline）。在这种小样本下，Mann-Whitney U 检验的统计功效（statistical power）有限。

### 假阳性 vs 假阴性

| 风险 | 后果 | 概率（估算） |
|------|------|------------|
| **假阳性**（采纳了一个无效的参数变更） | 多花了钱，但下一个测试周期会纠正 | ~5%（p < 0.05 阈值） |
| **假阴性**（拒绝了一个有效的参数变更） | 错过节省机会，7 天后重新提案 | ~20%（受限于小样本） |

设计上**优先避免假阳性**（不采纳坏变更），代价是偶尔错过好变更。实时 A/B 之前应先用历史 cost fingerprint 做 replay，减少把真实 API 花费用在明显无效提案上的概率。

### 缓解措施

| 措施 | 说明 |
|------|------|
| **保守阈值** | p < 0.05，不是 0.10 |
| **效果量门槛** | 必须 ≥5% 成本降低，不只是统计显著 |
| **低风险快速通道** | 影响 < $0.01/session 的变更不需要 A/B，直接应用 |
| **高分位数跟踪** | 除了均值，也检查 P90 成本——避免优化均值但恶化长尾 |
| **交叉验证** | 如果同一个参数的新提案与之前被拒绝的提案方向相反，延长时间窗口 |

---

## 8. MCP 安全风险

### 问题

MCP 服务器是子进程（stdio）或远程连接（SSE），带来了额外的攻击面。

| 风险 | 场景 | 严重程度 |
|------|------|---------|
| **命令注入** | 配置中的 `command` 参数被篡改 | 🔴 高 |
| **远程代码执行** | 恶意 MCP server 返回 `spawn_process` 工具 | 🔴 高 |
| **数据泄露** | MCP server 将数据传输到外部 | 🟡 中 |
| **资源耗尽** | MCP server 无限循环消耗 CPU/内存 | 🟡 中 |
| **SSE 中间人** | 远程 MCP 连接被劫持 | 🟡 中 |

### 缓解措施

| 措施 | 实现 |
|------|------|
| **配置只读** | MCP server 声明只在 `~/.sponge/config.toml` 中，不能从 prompt 注入 |
| **白名单命令** | 默认只允许 `npx`、`uvx`、`docker`——自定义命令需要用户确认 |
| **沙箱继承** | MCP 子进程运行在与 Sponge 相同的 sandbox 中（Docker/E2B） |
| **输出大小限制** | MCP tool 输出上限 1MB，超过截断 |
| **超时** | 每个工具调用默认 30s 超时 |
| **远程 server opt-in** | SSE/streamable-http 连接需要用户显式确认 URL |
| **定期健康检查** | 每 5 分钟 ping 一次 MCP server，失联则重启 |

### 不可消除的剩余风险

MCP 本质上是一个"运行任意代码"的协议。用户安装了恶意 MCP server，Sponge 无法防御——就像浏览器无法防御用户安装了恶意扩展一样。信任模型是：**用户对自己安装的 MCP server 负责**。

---

## 风险矩阵总览

| 风险 | 可能性 | 影响 | 缓解有效性 | 剩余风险 |
|------|--------|------|-----------|---------|
| 冷启动默认参数不佳 | 高 | 低 | 中 | 🟢 可接受 |
| 反馈回路偏离（压缩率/质量） | 中 | 中 | 中 | 🟡 需关注 |
| Provider 特性静默失效 | 中 | 中 | 高 | 🟢 可接受 |
| 成本估算不精确 | 低 | 低 | 高 | 🟢 可接受 |
| Embedding 供应商锁定 | 低 | 中 | 高 | 🟢 可接受 |
| A/B 测试成本 | 高 | 低 | 高 | 🟢 可接受 |
| 小样本统计噪声 | 中 | 低 | 中 | 🟢 可接受 |
| MCP 安全风险 | 低 | 高 | 高 | 🟡 需关注 |

**两个需要持续关注的风险：**
1. 反馈回路偏离——目前没有自动质量评估，依赖用户手动回滚
2. MCP 安全——第三方 server 质量参差不齐，用户教育是关键
