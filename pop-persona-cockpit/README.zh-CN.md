<!-- language-switch:start -->
[English](./README.md) | [中文](./README.zh-CN.md)
<!-- language-switch:end -->

# POP 角色驾驶舱

`POP Persona Cockpit` 是本地优先的 CLI，用于构建和使用个人数字角色工作区。
它现在还包括一个使用 FastAPI 和 Jinja2 构建的简单本地 Web shell。

这个 MVP 故意缩小范围：

- 一个用户
- 本地文件+SQLite
- 可读的 JSON 和 Markdown 输出
- 简单的 CLI 工作流程
- 默认没有云依赖

## v1 的范围

第一个版本侧重于四个核心工作：

1. 将聊天记录和笔记导入本地工作区
2. 提取结构化的日常角色信号
3. 保持稳定的`persona_core.json`
4. 在回答新问题之前注入角色上下文

每个角色辅助会话还应该留下审核跟踪。

## 项目布局

```text
pop-persona-cockpit/
  data/
    raw_logs/
    daily_notes/
    persona_core/
    sessions/
  src/pop_cockpit/
  tests/
```

## 设置

```bash
cd /Users/zhangbin/GitHub/pop-persona-cockpit
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

该仓库是使用 `python3` 进行本地搭建和验证的，它在本机上解析为 Python `3.14.3`。

## 命令行界面

脚手架公开了 `pop` 命令。

```bash
pop --help
pop status
pop import file ./example.txt
pop import folder ./sample-data
pop import chatgpt-export ~/Downloads/chatgpt-export.zip
python3 -m pop_cockpit.cli import file ./example.txt
pop extract daily --from 2026-03-20 --to 2026-03-22
pop extract backfill --from 2024-01-01 --to 2026-03-22 --source-type chatgpt_export
pop persona rebuild
pop persona show
pop persona export
pop persona rebuild --scope source_type:chatgpt_export
pop ask "What should I focus on today?"
pop web
```

导入命令在 v1 中实现。后面的角色命令仍然是占位符，将逐步完成。

导入规范化故意简单且确定：

- 文本和 Markdown 文件标准化行结尾并修剪外部空白
- 在可能的情况下，使用稳定的键排序来解析和重新序列化 JSON 文件

每日提取当前使用本地启发式回退提供程序，因此即使没有外部 API，快照字段也是确定性且可审查的。

每日提取是源时间感知的。有效的事件时间戳分辨率为：

1. 当 `metadata.created_at` 存在并解析为 ISO 时间戳时使用它
2. 否则回退到 `imported_at`

这可以防止历史 ChatGPT 消息崩溃到导入当天。

## 贮存

CLI 在首次运行时自动引导本地存储：

- SQLite数据库：`data/pop_persona.db`
- 原料进口：`data/raw_logs/`
- 每日笔记：`data/daily_notes/`
- 人物核心出口：`data/persona_core/`
- 会话工件：`data/sessions/`
- 网络/工作流程日志：`data/logs/`
- 本地设置：`data/settings.json`

## 本地网络用户界面

使用以下命令启动本地 Web shell：

```bash
pop web
```

然后打开：

```text
http://127.0.0.1:8765
```

Web UI 包装了现有的后端逻辑：

- 仪表板和工作流程状态
- 文件和 ChatGPT 导出导入
- 角色重建/导出
- 角色辅助提问
- 审核浏览
- 调度程序设置

## Chrome 捕获扩展程序

第 2 阶段在 `extension/` 下添加本地 Chrome 扩展。

它捕获 ChatGPT Web 对话的来源：

- `https://chatgpt.com/*`
- `https://chat.openai.com/*`

并将它们发送到本地后端：

- `POST /api/capture/chat-message`
- `GET /api/capture/status`

通过以下方式从 Chrome 加载它：

```text
chrome://extensions
```

然后启用开发者模式并为 `extension/` 目录选择 `Load unpacked`。

## 发展

运行测试：

```bash
pytest
```
