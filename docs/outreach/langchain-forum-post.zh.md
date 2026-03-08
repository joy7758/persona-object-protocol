# POP v0.1.7：面向 LangChain 的 Persona Object Execution Contract Surface

## 简短说明

POP 是一个面向 agent runtime 的 framework-neutral persona object
protocol。当前 `v0.1.7` 这条 release line 已经形成了一个面向
LangChain 的 execution contract surface，主入口是
`create_langchain_execution_bundle(...)`。

## POP 当前已经提供什么

- 一个由稳定 JSON Schema baseline 约束的 persona object 边界
- 一个已在真实 PyPI 公开分发的 Python 包
- 通过可选 `schema` extra 提供的严格 schema 校验
- 一个面向 LangChain 的 execution contract surface，并通过可选
  `langchain` extra 增强
- 无需真实模型调用的 installed-package smoke 路径

## 当前稳定边界

Python 包版本已经持续推进，但 canonical schema baseline 仍保持为
`v0.1.0`。也就是说，运行时 helper 和 execution surface 可以在
包版本层面继续演进，但 persona object 的核心结构边界目前保持
稳定。

## 为什么这可能与 LangChain 用户或维护者有关

POP 试图提供的是一个显式、可移植的人格对象层，而不是重定义
LangChain 的 runtime types。当前这条 LangChain-facing surface 更像
一层轻量 contract，可围绕 `create_agent`、middleware-facing helper
bundle 和 runtime-context scaffold 进行评估。

## POP 不主张什么

- POP 不是官方 LangChain 集成
- POP 不试图重写 LangChain runtime object 或 API
- POP 不承诺不同 runtime 之间的行为等价
- POP 不把 tools、memory、permissions 写进 persona-core

## 建议的评估路径

1. 安装 `pop-persona[langchain]`
2. 加载一个 canonical persona object
3. 运行围绕 `create_langchain_execution_bundle(...)` 的最小示例
4. 检查返回结构里的 `create_agent_kwargs`、`context_bundle` 和
   `middleware_bundle`

## 当前希望收到的反馈

最有价值的反馈主要集中在三点：

- LangChain 主入口对首次评估者是否足够清晰
- 当前 execution contract shape 是否足够贴近 LangChain v1 的现实
- installed-package-first smoke 路径是否足够清楚、足够低摩擦
