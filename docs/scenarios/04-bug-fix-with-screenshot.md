# 场景 4：Bug 修复（含截图）

> 展示了多模态输入——用户提供截图，Sponge 理解图像内容并修复对应的 bug。

---

## 命令

```bash
sponge run "这个按钮在移动端布局错位了，修复它" --image bug-report.png
```

## 期望输出

### 步骤 1：图像加载

```
📷 加载截图: bug-report.png (800×600, ~1,200 tokens)
```

### 步骤 2：分析截图

```
🔍 分析截图内容...
   检测到: 登录页面的"提交"按钮在 <768px 视口下超出容器边界
   定位: 缺少 `max-width: 100%` 和 `box-sizing: border-box`
```

### 步骤 3：读取源文件

```
📖 读取 src/components/SubmitButton.vue (67 行)
```

### 步骤 4：审批门（显示 diff）

```
❓ sponge 将修改 src/components/SubmitButton.vue
   ┌─ Diff ──────────────────────────────────────────────┐
   │  .submit-button {                                    │
   │  +   max-width: 100%;                                │
   │  +   box-sizing: border-box;                         │
   │  }                                                   │
   └──────────────────────────────────────────────────────┘
   Approve? [Y/n] Y
```

### 步骤 5：验证

```
🔧 运行测试...
   ✓ 单元测试: 通过 (8/8)
   ✓ 视觉回归: 未检测到新的不一致
```

### 步骤 6：成本报告

```
⏱ 12.1s · $0.0362

═══════════════════════════════════════════
  Session Cost Report
═══════════════════════════════════════════
  Total cost:           $0.0362
  Tokens in:            2,430  (1,200 = 截图)
  Tokens out:             240

  Savings vs naive:     $0.0891  (71.1%)
  Image tokens:         1,200  (32.5% of input)
═══════════════════════════════════════════
```

## 发生了什么

| 步骤 | 说明 |
|------|------|
| 1. 图像编码 | CLI 将 `bug-report.png` 编码为 base64 data URI，放入 ContentBlock |
| 2. 多模态理解 | Opus 4.7 分析截图中的像素 → 识别布局问题 |
| 3. 代码定位 | 模型根据截图 + 项目结构找到对应的 CSS 文件 |
| 4. 编辑 | 插件 file_read + file_write（经审批门确认） |
| 5. 验证 | Shell 插件运行测试 + 视觉回归检查 |

## 关键观察

- **截图 = 1,200 tokens**——比 1,000 字的文本描述更贵（~$0.018 vs ~$0.003），但更准确
- **图像不能缓存的可压缩性有限**——`bug-report.png` 每次重新分析成本一致；减少截图尺寸（800×600 而不是 4K）可降低 token 成本
- **如果截图被压缩管线丢弃**——管线会保留最近 3 轮中的图像，不会在第一次分析时就丢掉

## 变体：多张截图

```bash
# 同时提供"错误"和"正确"的对比
sponge run "修复布局" --image bug.png --image expected.png

# 附上设计稿
sponge run "按设计稿调整样式" --image spec.png

# 附上 PDF 需求文档
sponge run "实现这个 API" --file api-spec.pdf
```
