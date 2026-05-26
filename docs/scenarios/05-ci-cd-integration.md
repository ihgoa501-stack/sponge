# 场景 5：CI/CD 集成

> 展示了 Sponge 在 CI/CD 管道中的非交互式使用——没有流式输出、自动批准、JSON 格式输出。

---

## 场景

在 CI pipeline 中自动修复 lint 错误和类型错误。

## CI 配置

```yaml
# .github/workflows/lint-fix.yml
name: Auto-fix lint & type errors

on:
  pull_request:
    paths: ["src/**/*.py"]

jobs:
  auto-fix:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev]"

      # 运行 Sponge 自动修复
      - name: Auto-fix lint errors
        run: |
          sponge run "修复 src/ 中所有的 ruff lint 错误" \
            --no-stream \
            --auto-approve \
            --json > fix-report.json

      # 提交修复（如果有变更）
      - name: Commit fixes
        run: |
          if [ -n "$(git status --porcelain)" ]; then
            git config user.name "sponge-bot"
            git config user.email "bot@sponge.ai"
            git add -A
            git commit -m "chore: auto-fix lint errors [sponge]"
            git push
          fi

      # 检查修复成本（可选：如果成本异常高则告警）
      - name: Check fix cost
        run: |
          cost=$(jq '.total_cost' fix-report.json)
          if (( $(echo "$cost > 1.0" | bc -l) )); then
            echo "⚠️ 修复成本异常: $cost (阈值 $1.00)"
          else
            echo "✅ 修复成本: $cost"
          fi
```

## Sponge 命令

```bash
sponge run "修复 src/ 中所有的 ruff lint 错误" \
  --no-stream \
  --auto-approve \
  --json
```

## 期望输出（JSON）

```json
{
  "session_id": "sess_ci_20260523_001",
  "status": "completed",
  "total_cost": 0.1842,
  "tokens_in": 8240,
  "tokens_out": 2150,
  "steps": 12,
  "savings": {
    "cache": 0.0421,
    "compression": 0.0310,
    "plugin_routing": 0.0600,
    "total_vs_naive": 0.1331,
    "savings_pct": 72.2
  },
  "tools_executed": [
    {
      "tool": "builtins.shell.exec",
      "command": "ruff check src/ --select E,F,W --output-format=json",
      "result": "found 23 errors",
      "cost": 0.0000,
      "approval": "auto-approved"
    },
    {
      "tool": "builtins.file_ops.read_file",
      "path": "src/main.py",
      "lines": 342,
      "cost": 0.0000,
      "approval": "auto-approved"
    },
    {
      "tool": "builtins.file_ops.write_file",
      "path": "src/main.py",
      "diff_lines": 5,
      "cost": 0.0000,
      "approval": "auto-approved"
    }
  ],
  "summary": "Fixed 23 lint errors across 8 files. All fixes are safe (auto-format only, no logic changes)."
}
```

## 成本分析

```
任务: 修复 23 个 lint 错误

成本分解:
  ├─ LLM 调用 (分析 + 生成 fix):  $0.1842
  ├─ Shell 命令 (ruff, git):       $0.0000  ← 插件
  ├─ 文件读写 (8 个文件):         $0.0000  ← 插件
  └─ 总计:                         $0.1842

对比: 人工修复 23 个 lint 错误 ≈ 15 分钟开发时间
      15 分钟 × $50/小时 ≈ $12.50 人力成本
      Sponge 成本 = $0.18
      投资回报率: ~70x
```

## 关键观察

- **`--no-stream`**——CI 环境中不需要流式输出，全部缓冲后一次性输出
- **`--auto-approve`**——CI 中没人坐在终端前点确认。用户信任 lint 修复是安全的
- **`--json`**——结构化输出方便下游（告警、报表、成本追踪）
- **所有 shell/file 操作零成本**——插件路由让这些操作不走 LLM
- **缓存效果**——如果同一个 PR 触发多次重建，第二次运行缓存中存的系统 prompt 和工具定义 → 成本减半

## 安全考虑

```yaml
# 更安全的 CI 配置（只读 + 手动批准写操作）
- name: Security audit (read-only)
  run: |
    sponge run "审查这个 PR 的安全漏洞" \
      --no-stream \
      --read-only \
      --json > audit-report.json

# 交互式审批（需要 GitHub Actions 的 approval）
- name: Apply security fixes
  run: |
    sponge run "修复 audit-report.json 中发现的漏洞" \
      --no-stream \
      --approval-policy=security-patch \
      --json
```

`--read-only` 模式拒绝所有写操作，适合安全审查阶段。
