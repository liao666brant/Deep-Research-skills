---
name: research-deep
description: 按调研大纲分批启动子代理搜索，并校验每个对象的 JSON 结果。
---

# 深度调研

## 执行流程

### 1. 自动定位Outline
在当前工作目录查找 `*/outline.yaml` 文件，读取items列表、execution配置（含items_per_agent）。

### 2. 断点续传检查
- 检查output_dir下已完成的JSON文件
- 跳过已完成的items

### 3. 分批执行
- 按batch_size分批（完成一批需要得到用户同意才可进行下一批）
- 每个agent负责items_per_agent个项目
- 在后台并行启动内置 `worker` 子代理。让子代理先读取当前技能目录下 `../../references/web-researcher.md`（传入解析后的绝对路径），再执行搜索任务。只向用户汇总进度与结果。

**参数获取**：
- `{topic}`: outline.yaml中的topic字段
- `{item_name}`: item的name字段
- `{item_related_info}`: item的完整yaml内容（name + category + description等）
- `{output_dir}`: outline.yaml中execution.output_dir（默认./results）
- `{fields_path}`: {topic}/fields.yaml的绝对路径
- `{output_path}`: {output_dir}/{item_name_slug}.json的绝对路径（slugify处理item_name：空格替换为_，移除特殊字符）
- `{validator_path}` 为从当前技能目录解析 `../research/validate_json.py` 得到的绝对路径。

**硬约束**：以下prompt必须严格复述，仅替换{xxx}中的变量，禁止改写结构或措辞。

**提示词模板**：
```python
prompt = f"""## 任务
调研 {item_related_info}，输出结构化JSON到 {output_path}

## 字段定义
读取 {fields_path} 获取所有字段定义

## 输出要求
1. 按fields.yaml定义的字段输出JSON
2. 不确定的字段值标注[不确定]
3. JSON末尾添加uncertain数组，列出所有不确定的字段名
4. 所有字段值必须使用中文输出（调研过程可用英文，但最终JSON值为中文）

## 输出路径
{output_path}

## 验证
完成JSON输出后，运行验证脚本确保字段完整覆盖：
python3 "{validator_path}" -f "{fields_path}" -j "{output_path}"
验证通过后才算完成任务。
"""
```

**完整示例**（假设调研GitHub Copilot）：
```
## 任务
调研 name: GitHub Copilot
category: 国际产品
description: Microsoft/GitHub开发，首个主流AI编程助手，市场份额约40%，输出结构化JSON到 {project_dir}/results/GitHub_Copilot.json

## 字段定义
读取 {project_dir}/fields.yaml 获取所有字段定义

## 输出要求
1. 按fields.yaml定义的字段输出JSON
2. 不确定的字段值标注[不确定]
3. JSON末尾添加uncertain数组，列出所有不确定的字段名
4. 所有字段值必须使用中文输出（调研过程可用英文，但最终JSON值为中文）

## 输出路径
{project_dir}/results/GitHub_Copilot.json

## 验证
完成JSON输出后，运行验证脚本确保字段完整覆盖：
python3 "{validator_path}" -f "{project_dir}/fields.yaml" -j "{project_dir}/results/GitHub_Copilot.json"
验证通过后才算完成任务。
```

### 4. 等待与监控
- 等待当前批次完成
- 启动下一批
- 显示进度

### 5. 汇总报告
全部完成后输出：
- 完成数量
- 失败/不确定标记的items
- 输出目录
