# POP v0.1.0-v0.1.4 Evolution Note

## 中文版

### 概览

这份纪要概括 POP 从 `v0.1.0` 到 `v0.1.4` 的早期演化路径。它的核心意义不在于“功能越来越多”，而在于 POP 逐步建立了清晰的协议边界、分发能力、治理纪律，以及面向主流 agent runtime 的执行层表面。

在整个 `v0.1.x` 序列中，POP 一直保持一个关键约束：

- Python package release 持续前进
- canonical schema baseline 保持为 `v0.1.0`

这意味着 POP 的结构边界没有随着每次发布被反复重写，而是在稳定边界上持续推进工具层与运行时层。

### v0.1.0

`v0.1.0` 建立了 POP 的第一个 canonical schema baseline。这个版本的重点是：

- 定义 persona object 的正式结构边界
- 引入 canonical JSON Schema 与严格校验路径
- 建立 versioned schema、fixture corpus 和 CI gate
- 让 POP 从“文档性草案”变成“有结构裁判面的协议草案”

### v0.1.1

`v0.1.1` 是一次 packaging 与 installability 修复版本。它没有改变 schema baseline，而是把 POP 推进到真实公开分发状态：

- 修复 installable package 中的 schema 资源打包问题
- 保证安装态可见 schema 版本信息
- 保证安装态 strict-schema 校验可用
- 完成真实 PyPI 分发与安装烟测

这一版的意义是：POP 不再只是仓库内协议，而是一个可公开安装、可严格校验的协议包。

### v0.1.2

`v0.1.2` 建立了 runtime binding surface。它没有改变 top-level persona boundary，而是开始把 canonical persona object 投影到 runtime-facing 表达：

- 增加 LangChain 与 CrewAI 的 runtime integration scaffolds
- 保持 dependency-light，不要求真实网络调用
- 让 POP 从“可安装协议包”进入“可绑定 runtime 的 persona object layer”

### v0.1.3

`v0.1.3` 建立了 execution-layer helper surface。它把上一版的 binding surface 再向前推进一步：

- 引入 execution-layer helpers
- 补 execution examples 与 dependency-light smoke tests
- 继续保持 schema baseline 稳定

这一版的意义是：POP 开始具备“如何把 persona object 带到执行层”的明确帮助面。

### v0.1.4

`v0.1.4` 把主轴收束到 LangChain，并形成 LangChain optional-dependency execution release：

- 增加面向 LangChain v1 `create_agent` / middleware / runtime-context 的早期 execution helpers
- 保持 `langchain` 为 optional extra，不污染 core 包
- 通过 dependency-aware smoke tests 证明 helper 具有执行层可消费结构
- 将旧 LangChain scaffold helpers 降级为 compatibility helpers

这一版的意义是：POP 不仅可安装、可严格校验，而且开始在主流 agent runtime 上形成真实 optional-dependency execution surface。

### 当前阶段判断

到 `v0.1.4` 为止，POP 已经形成了一条清晰的早期演化链：

- `v0.1.0`: schema baseline
- `v0.1.1`: public distribution
- `v0.1.2`: runtime binding surface
- `v0.1.3`: execution-layer helper surface
- `v0.1.4`: LangChain-focused optional execution surface

这条演化链说明，POP 正在沿着“persona object layer -> runtime binding -> execution helper -> optional runtime integration”这条路径稳定推进，而不是反复改写协议边界。

## English

### Overview

This note summarizes the early evolution of POP from `v0.1.0` to `v0.1.4`. The main significance of this sequence is not feature accumulation, but the progressive establishment of protocol boundaries, public distribution, governance discipline, and runtime-facing execution surfaces.

Across the `v0.1.x` line, POP has kept one important constraint stable:

- the Python package release may advance
- the canonical schema baseline remains `v0.1.0`

This means the structural contract has remained stable while tooling and runtime-facing layers continue to evolve on top of it.

### v0.1.0

`v0.1.0` established the first canonical schema baseline for POP. Its main contributions were:

- defining the formal structural boundary of a persona object
- introducing a canonical JSON Schema and strict validation path
- adding versioned schema snapshots, a fixture corpus, and a CI gate
- moving POP from a documentation-only draft toward a protocol draft with a formal validation boundary

### v0.1.1

`v0.1.1` was a packaging and installability fix release. It did not change the schema baseline. Instead, it moved POP into real public distribution:

- fixing packaged schema resource inclusion
- restoring installed-package visibility of available schema versions
- restoring installed-package strict-schema validation
- completing real PyPI publication and installation smoke validation

This release marked the transition from a repository-local protocol draft to a publicly installable and strict-schema-validatable package.

### v0.1.2

`v0.1.2` established the runtime binding surface. It did not change the canonical top-level persona boundary. Instead, it began to project canonical persona objects into runtime-facing representations:

- early LangChain and CrewAI runtime integration scaffolds
- dependency-light helper surfaces without requiring live network calls
- a first move from a distributable protocol package toward a runtime-bindable persona object layer

### v0.1.3

`v0.1.3` established the execution-layer helper surface. It pushed the runtime-facing line one step further:

- execution-layer helper surfaces
- local execution examples and dependency-light smoke tests
- continued stability of the schema baseline

This release marked the point where POP began to expose a clearer surface for bringing persona objects into execution-oriented flows.

### v0.1.4

`v0.1.4` narrowed the primary line to LangChain and became a LangChain-focused optional-dependency execution release:

- early execution helpers aligned with LangChain v1 `create_agent`, middleware, and runtime-context surfaces
- continued separation of `langchain` as an optional extra rather than a core dependency
- dependency-aware smoke tests showing that the helper outputs are consumable execution-side structures
- explicit downgrade of older LangChain scaffold helpers to compatibility status

This release marked the transition from a package that can be installed and validated to one that begins to expose a real optional-dependency execution surface for a mainstream agent runtime.

### Current Position

By `v0.1.4`, POP has formed a coherent early evolution line:

- `v0.1.0`: schema baseline
- `v0.1.1`: public distribution
- `v0.1.2`: runtime binding surface
- `v0.1.3`: execution-layer helper surface
- `v0.1.4`: LangChain-focused optional execution surface

Taken together, this sequence shows that POP is advancing along a stable path:

persona object layer -> runtime binding -> execution helper -> optional runtime integration

rather than repeatedly redefining its canonical schema boundary.
