> ⚠️ **Draft** — Describes planned Phase 3+ behavior (memory, multi-step approval). See [project-plan.md](../project-plan.md).

# 场景 3：多步重构 + 记忆

> 展示了多步重构过程：读取文件 → 分析 → 修改 → 验证。同时展示了长期记忆如何阻止重复错误。

---

## 背景

用户在 `memory.toml` 中已经有一条规则：

```toml
[rules]
http_lib = "Use httpx, not requests"
```

## 命令

```bash
sponge run "把 src/fetcher.py 中的网络请求从 requests 改为 httpx"
```

## 期望输出

### 步骤 1：记忆注入

```
📌 项目记忆已加载 (1 条规则)
   • Use httpx, not requests  ← 自动注入 system prompt
```

### 步骤 2：读取源文件

```
📖 读取 src/fetcher.py (142 行)
```

### 步骤 3：审批门（写文件）

```
❓ sponge 将修改 src/fetcher.py
   ┌─ Diff ──────────────────────────────────────────────┐
   │  - import requests                                   │
   │  + import httpx                                      │
   │                                                     │
   │  - def fetch(url):                                   │
   │  -     resp = requests.get(url, timeout=5)            │
   │  -     return resp.json()                             │
   │  + async def fetch(url):                              │
   │  +     async with httpx.AsyncClient() as client:      │
   │  +         resp = await client.get(url, timeout=5)   │
   │  +         return resp.json()                         │
   └──────────────────────────────────────────────────────┘
   Approve? [Y/n] (o)nce / (a)llow always / (n)ever
```

### 步骤 4：用户输入

```
Y  ← 确认本次修改
```

### 步骤 5：验证

```
🔧 运行 lint + typecheck...
   ✓ ruff --fix: 通过
   ✓ mypy --strict: 通过
   ⚠️ pytest: 2 个测试失败（需要更新 mock）
```

### 步骤 6：修复测试

```
❓ sponge 将修改 tests/test_fetcher.py
   ┌─ Diff ──────────────────────────────────────────────┐
   │  - @patch('requests.get')                             │
   │  + @patch('httpx.AsyncClient.get')                           │
   │  - mock_response.json.return_value = {"key": "val"}  │
   │  + mock_response.raise_for_status.return_value = None│
   └──────────────────────────────────────────────────────┘
   Approve? [Y/n] Y
```

### 步骤 7：全部通过

```
✓ ruff --fix: 通过
✓ mypy --strict: 通过
✓ pytest: 通过 (12/12)
✓ 重构完成
```

### 步骤 8：成本报告

```
⏱ 24.3s · $0.0872

═══════════════════════════════════════════
  Session Cost Report
═══════════════════════════════════════════
  Total cost:           $0.0872
  Tokens in:            6,210
  Tokens out:           1,024
  Savings vs naive:     $0.2150  (71.1%)

  Steps: 4 (read → edit → verify → fix test)
  All modifications: approved by user
═══════════════════════════════════════════
```

## 发生了什么

| 步骤 | 说明 |
|------|------|
| 1. Memory injection | 项目记忆中的 `http_lib` 规则注入 system prompt，告诉模型用 httpx |
| 2. Plugin route | `file_read` → 零成本插件 |
| 3. Approval gate | `file_write` → Confirm 梯级 → 显示 diff → 用户确认 |
| 4. Shell exec | 运行 lint/typecheck/test → 零成本插件 |
| 5. Test fix | 模型自动检测测试失败并建议修复 |
| 6. Approval gate | 再次确认写 tests/test_fetcher.py |

## 关键观察

- **记忆阻止了错误**——如果 memory.toml 没有 `http_lib` 规则，模型可能用 `requests` 重写一遍。记忆注入确保一致性。
- **每次写文件都触发审批门**——用户看到了所有变更，没有意外修改
- **如果没有记忆**——用户需要在 prompt 中说"用 httpx 不要用 requests"。记忆让这个规则跨 session 生效
- **总节省 71.1%**——插件（file_read, shell exec）零成本 + 压缩 + prompt cache

## 记忆的长期效果

```
Session 1: "把 requests 改成 httpx" → 用户手动告诉模型
           (cost: $0.0872)

Session 2: 用户添加 memory 规则
           sponge memory add "Use httpx, not requests" --key http_lib

Session 3: "添加新的 API 调用" → 模型自动用 httpx
           (cost: $0.0510, 节省来自不需要重复说明)

Session 4: "重构另一个文件" → 模型继续用 httpx
           (cost: $0.0421, 记忆命中 + 缓存命中)
```
