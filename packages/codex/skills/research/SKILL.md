---
name: research
description: 对目标话题进行初步调研，生成调研outline。用于学术调研、benchmark调研、技术选型等场景。
---

# 初步调研

## 执行流程

需要用户确认时优先使用 `request_user_input`。工具不可用时，在对话中提问并等待回复。

用简体中文说明调研范围，并撰写调研对象和字段的描述。保留专有名称和 YAML 键名。

### 1. 模型内部知识生成初步框架
基于topic，利用模型已有知识生成：
- 该领域的主要研究对象/items列表
- 建议的调研字段框架

输出{step1_output}，使用request_user_input确认：
- items列表是否需要增减？
- 字段框架是否满足需求？

### 2. Web Search补充
使用request_user_input询问时间范围（如：最近6个月、2024年至今、不限）。

**参数获取**：
- `{topic}`: 用户输入的调研话题
- `{YYYY-MM-DD}`: 当前日期
- `{step1_output}`: Step 1生成的完整输出内容
- `{time_range}`: 用户指定的时间范围

**硬约束**：以下prompt必须严格复述，仅替换{xxx}中的变量，禁止改写结构或措辞。

在后台启动一个内置 `default` 子代理。让子代理先读取当前技能目录下 `../../references/web-researcher.md`（传入解析后的绝对路径），再执行搜索任务。

**提示词模板**：
```python
prompt = f"""## 任务
调研话题: {topic}
当前日期: {YYYY-MM-DD}

基于以下初步框架，补充最新items和推荐调研字段。

## 已有框架
{step1_output}

## 目标
1. 验证已有items是否遗漏重要对象
2. 根据遗漏对象进行补充items
3. 继续搜索{topic}相关且{time_range}内的items并补充
4. 补充新fields

## 输出要求
直接返回结构化结果（不写文件）：

### 补充Items
- item_name: 简要说明（为什么应该加入）
...

### 推荐补充字段
- field_name: 字段描述（为什么需要这个维度）
...

### 信息来源
- [来源1](url1)
- [来源2](url2)
"""
```

**完整示例**（假设调研AI Coding发展史）：
```
## 任务
调研话题: AI Coding 发展史
当前日期: 2025-12-30

基于以下初步框架，补充最新items和推荐调研字段。

## 已有框架
### Items列表
1. GitHub Copilot: Microsoft/GitHub开发，首个主流AI编程助手
2. Cursor: AI-first IDE，基于VSCode
...

### 字段框架
- 基本信息: name, release_date, company
- 技术特性: underlying_model, context_window
...

## 目标
1. 验证已有items是否遗漏重要对象
2. 根据遗漏对象进行补充items
3. 继续搜索AI Coding 发展史相关且2024年至今内的items并补充
4. 补充新fields

## 输出要求
直接返回结构化结果（不写文件）：

### 补充Items
- item_name: 简要说明（为什么应该加入）
...

### 推荐补充字段
- field_name: 字段描述（为什么需要这个维度）
...

### 信息来源
- [来源1](url1)
- [来源2](url2)
```

### 3. 询问用户已有字段
使用request_user_input询问用户是否有已定义的字段文件，如有则读取并合并。

### 4. 生成Outline（分离文件）
合并{step1_output}、{step2_output}和用户已有字段，生成两个文件：

**outline.yaml**（items + 配置）：
- topic: 调研主题
- items: 调研对象列表
- execution:
  - batch_size: 并行agent数量（需request_user_input确认）
  - items_per_agent: 每个agent调研项目数（需request_user_input确认）
  - output_dir: 结果输出目录（默认./results）

**fields.yaml**（字段定义）：
- 字段分类和定义
- 每个字段的name、description、detail_level
- detail_level 的取值依次为 `brief`、`moderate`、`detailed`
- uncertain: 不确定字段列表（保留字段，deep阶段自动填充）

### 5. 输出并确认
- 创建目录: `./{topic_slug}/`
- 保存: `outline.yaml` 和 `fields.yaml`
- 展示给用户确认

## 输出路径
```
{当前工作目录}/{topic_slug}/
  ├── outline.yaml    # items列表 + execution配置
  └── fields.yaml     # 字段定义
```

## 后续技能
- `research-add-items` - 补充items
- `research-add-fields` - 补充字段
- `research-deep` - 开始深度调研
