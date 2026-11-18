# 启动网页调研子代理

- 在 Claude Code 中调用插件代理 `deep-research:web-search-agent`，把调研任务交给它。
- 在 OpenCode 中调用内置 `general` 子代理。保留调用方的任务模板，并附上本目录下 `web-search-modules/` 和 `../agents/web-search-agent.md` 的绝对路径。让子代理先读取代理说明的正文，再用 OpenCode 提供的文件读取和网页搜索工具执行。
