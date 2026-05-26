# 场景 2：代码审查

> 使用 sub-agent 进行代码审查，浓缩结果后发给最佳模型。展示了 sub-agent dispatch、condensation、approval gate 的交互。

---

## 命令

```bash
sponge run "审查 src/auth/login.ts 这个文件，找安全漏洞"
```

## 期望输出

### 步骤 1：任务分析

```
🔍 分析任务...
   检测到: 代码审查任务 → 使用 sub-agent 进行初步分析
   匹配插件: review (sub-agent)
```

### 步骤 2：审批门（sub-agent 需要读取文件）

```
❓ sponge 需要读取 src/auth/login.ts
   Path: src/auth/login.ts
   Approve? [Y/n] Y
```

### 步骤 3：Sub-agent 执行（在隔离上下文中）

```
🔧 Sub-agent: 分析 src/auth/login.ts...
   ── 扫描安全模式 ──
   ✓ 输入验证: 发现 3 个 sanitization 调用
   ⚠️ JWT 处理: 硬编码密钥在 login.ts:42
   ⚠️ SQL 查询: 字符串拼接在 login.ts:78
   ✓ CSRF 保护: 已实现
   ── 生成审查报告 ──
```

### 步骤 4：Sub-agent 结果浓缩

```
📦 Sub-agent 返回: 1,240 行分析 → 浓缩为 320 字报告
   节省: 3,720 tokens (92.1% 压缩)
```

### 步骤 5：最佳模型生成最终审查（流式）

```
## 安全审查报告: src/auth/login.ts

### 🔴 高危: JWT 密钥硬编码 (第 42 行)
`const SECRET = "super-secret-key-12345"`
→ 使用环境变量: `process.env.JWT_SECRET`

### 🟡 中危: SQL 拼接注入风险 (第 78 行)
`"SELECT * FROM users WHERE id=" + userId`
→ 使用参数化查询: `db.query("SELECT * FROM users WHERE id=?", [userId])`

### ✅ 通过检查
- 输入验证 (3 处 sanitization): ✅
- CSRF 保护: ✅
- 密码哈希: ✅ (bcrypt, cost=12)

### 预估修复时间: 15 分钟
```

### 步骤 6：成本报告

```
⏱ 8.7s · $0.0341

═══════════════════════════════════════════
  Session Cost Report
═══════════════════════════════════════════
  Total cost:           $0.0341
  Tokens in:            2,812 (sub-agent) + 320 (condensed)
  Tokens out:             380

  Savings breakdown:
  ├─ Sub-agent condensation  $0.0422  (55.3%)  ← 关键节省
  ├─ Plugin routing           $0.0000  (0.0%)
  ├─ Cache savings           $0.0072  (9.4%)
  └─ Total vs naive:         $0.0494  (59.1%)
═══════════════════════════════════════════
```

## 发生了什么

| 步骤 | 子系统 | 说明 |
|------|--------|------|
| 1 | PluginRegistry | "审查"匹配到 `review` sub-agent 插件 |
| 2 | ApprovalGate | `file_read` 触发 Confirm 梯级 → 用户确认 |
| 3 | SubAgent | DeepSeek V4-Flash 在隔离上下文中分析文件 |
| 4 | Condensation | 1,240 行输出 → 320 字结构化报告 |
| 5 | LLM.stream() | Opus 4.7 基于浓缩报告生成最终审查 |
| 6 | CostTracker | 记录所有成本 + 节省分解 |

## 关键观察

- **59.1% 的节省来自 sub-agent condensation**——如果直接把文件塞给 Opus，输入 token 是 3,132（文件）+ overhead，成本翻倍
- **Sub-agent 使用 DeepSeek V4-Flash**（$0.14/MTok），成本是 Opus 的 1%
- **Approval gate 在文件读取时触发**——sub-agent 不能偷偷读取文件
- **如果重复审查同一文件** → 结果缓存命中 → $0.00

## 变体：批量审查

```bash
# 审查整个 src/ 目录（sub-agent 逐个文件分析，结果合并）
sponge run "审查 src/ 目录下所有 .ts 文件的安全漏洞"

# 差异对比审查（只看 PR 变更的部分）
sponge run "审查这个 PR 的变更" --image pr-diff.png
```
