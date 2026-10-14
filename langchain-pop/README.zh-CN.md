<!-- language-switch:start -->
[English](./README.md) | [中文](./README.zh-CN.md)
<!-- language-switch:end -->

# 朗链流行音乐

[角色对象协议](https://github.com/joy7758/persona-object-protocol) 的瘦适配器和兼容性包装器。

## 角色

`langchain-pop` 为想要最小 POP 集成入口点的 LangChain 用户保留了独立的封装表面。它的存在是为了暴露集成粘合和迁移连续性，而不是重新定义角色对象协议本身。

## 规范主页

规范的实现现在位于 `persona-object-protocol` 的 POP 集成界面和示例下：

- `persona-object-protocol/integrations/langchain-pop`
- `persona-object-protocol/src/pop/integrations/langchain`

## 不是这个仓库

- 不是规范的角色协议实现
- 不是架构总仓
- 不是基准套件
- 不是治理或审计层

## 最少使用量

```bash
pip install langchain-pop
python examples/langchain_middleware_demo.py --print-config
```

```python
from langchain_openai import ChatOpenAI

from langchain_pop.agent import create_pop_agent

agent = create_pop_agent(
    pop_source="tests/fixtures/mentor.v1.json",
    model=ChatOpenAI(model="gpt-4o", temperature=0.0),
    tools=[],
)
```

对于当前的协议上下文、模式演变和集成指南，请从 `persona-object-protocol` 开始，并将此仓库视为兼容性包装器。

## 地位

- 已弃用的独立包装器
- 规范主页是 `persona-object-protocol`
- 保留包装连续性和精简集成示例

## 笔记

- 独立包目前仍可安装。
- 协议语义、模式和规范示例位于 `persona-object-protocol` 中。
- 未来的合并可能会将此包装器完全折叠到父仓库中。
