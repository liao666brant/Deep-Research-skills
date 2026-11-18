---
name: research-add-items
description: 向现有调研outline补充items（调研对象）。
---

# 补充调研对象

## 执行流程

### 1. 自动定位Outline
在当前工作目录查找 `*/outline.yaml` 文件，自动读取。

### 2. 并行获取补充来源
同时进行：
- **A. 询问用户**：需要补充哪些items？有具体名称吗？
- **B. 询问是否需要Web Search**：是否启动内置 `default` 子代理搜索更多调研对象？用户同意后，让子代理先读取当前技能目录下 `../../references/web-researcher.md`（传入解析后的绝对路径），再执行搜索任务。

### 3. 合并更新
- 将新items追加到outline.yaml
- 展示给用户确认
- 避免重复
- 保存更新后的outline

## 输出
更新后的 `{topic}/outline.yaml` 文件（原地修改）
