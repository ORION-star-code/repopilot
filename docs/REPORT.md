# RepoPilot 技术架构报告

> 作者视角：Agent 架构师
> 日期：2026-05-27
> 版本：v0.1.0

---

## 一、项目定位

RepoPilot 是一个面向生产环境的 **AI 编程智能体（Coding Agent）**，专注于 Issue 驱动的 GitHub 仓库自动修复。给定一个 Bug Issue 或自然语言描述，系统能够自主完成：代码拉取 → 结构分析 → 上下文检索 → 修复计划生成 → 代码补丁 → 测试执行 → 失败反思与重试 → 产出 Git Diff / 测试报告 / PR 描述。

核心设计理念：**确定性工作流编排 + 审批门控 + 工具隔离 + 可观测性**。

---

## 二、技术栈实现

### 2.1 运行时与语言

| 层级 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | 类型提示成熟，标准库覆盖 CLI/子进程/路径操作，生态丰富 |
| 数据模型 | Pydantic v2 | 零成本校验、JSON Schema 自动生成、strict mode 类型安全 |
| Web 框架 | FastAPI | 异步原生、依赖注入、OpenAPI 自动生成，为未来 API 服务预留 |
| 代码质量 | ruff + mypy strict | ruff 替代 flake8+isort+pyupgrade，mypy 严格模式保证类型完整 |
| 测试框架 | pytest | 标准选型，配合 httpx 进行异步 API 测试 |
| 构建系统 | setuptools (pyproject.toml) | PEP 621 标准，`pip install -e ".[dev]"` 一键安装 |

### 2.2 目标生产栈（已架构预留）

当前版本是功能完整的骨架，以下组件已通过 Protocol/接口边界预留接入点：

| 组件 | 目标技术 | 当前状态 |
|------|----------|----------|
| LLM 推理 | OpenAI Agents SDK | `agents/prompts.py` 已定义 Prompt 模板，编排层确定性 |
| GitHub 集成 | GitHub App (PyJWT + httpx) | `github/client.py` Protocol + NoopClient |
| 沙箱隔离 | Docker SDK | `sandbox/executor.py` Protocol，当前 subprocess 执行 |
| 向量检索 | PostgreSQL + pgvector | `retrieval/contracts.py` Protocol + LocalCodeRetriever |
| 缓存/队列 | Redis + Celery/Dramatiq | `runs/manager.py` 预留持久化接口 |
| 可观测性 | OpenTelemetry | `observability/events.py` TraceEvent 结构化日志 |
| 评估系统 | Golden Dataset + LLM-as-Judge | `evaluation/contracts.py` 评估指标与用例模型 |

### 2.3 质量保障工具链

```
python scripts/check.py
├── ruff check          # Lint (E/F/I/UP rules, 100 字符行宽)
├── mypy src/           # 严格类型检查
├── pytest -q           # 65 个离线测试
└── harness/validate.py # 项目契约验证（文件结构、features.json、WIP=1）
```

---

## 三、系统架构

### 3.1 分层架构图

```
┌─────────────────────────────────────────────────────────┐
│                    入口层 (Entrypoints)                    │
│         CLI (argparse)    │    FastAPI (ASGI)             │
├─────────────────────────────────────────────────────────┤
│                 Run Manager (运行管理)                     │
│        RunRecord 生命周期 · 状态机 · 审批标记               │
├─────────────────────────────────────────────────────────┤
│           Workflow Orchestrator (工作流编排)                │
│  INTAKE → ANALYZE → RETRIEVE → PLAN → PATCH → TEST      │
│                                    ↑          ↓          │
│                                    └── REFLECT ┘          │
│                                  (失败反思 · 有界重试)       │
├─────────────────────────────────────────────────────────┤
│                    子系统层 (Subsystems)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ Issue     │ │ Repo     │ │ Retrieval│ │ Agent    │   │
│  │ Intake    │ │ Analysis │ │ (搜索)    │ │ Roles    │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
├─────────────────────────────────────────────────────────┤
│                    工具层 (Tool Layer)                     │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐│
│  │ File   │ │ Search │ │ Patch  │ │ Test   │ │ Git    ││
│  │ R/W/L  │ │ KW+grep│ │ diff   │ │ Runner │ │ ops    ││
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘│
├─────────────────────────────────────────────────────────┤
│                    安全层 (Safety)                        │
│  ApprovalPolicy · ExecutionMode · Sandbox · 审计日志      │
├─────────────────────────────────────────────────────────┤
│                    产出层 (Artifacts)                      │
│  diff.patch · test_report · risk_assessment · PR desc    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 核心工作流状态机

```
INTAKE ──→ ANALYZE ──→ RETRIEVE ──→ PLAN ──→ PATCH ──→ TEST ──→ REPORT
                                              ↑          ↓
                                              └── REFLECT ┘
                                              (max N retries)
```

- **INTAKE**：解析 GitHub Issue URL（正则）或原始 Bug 文本，生成 `RepairRequest`
- **ANALYZE**：扫描目标仓库，构建 `RepoSnapshot`（文件分类、语言统计、关键文件排名）
- **RETRIEVE**：基于关键词在代码中检索相关片段，返回带评分的 `RetrievedContext`
- **PLAN**：生成 `RepairPlan`（验证命令、补丁策略、测试策略）
- **PATCH**：应用 Unified Diff 到目标文件（审批门控）
- **TEST**：在沙箱中执行验证命令（审批门控，支持超时/输出捕获）
- **REFLECT**：测试失败时分析错误，调整策略，回到 PATCH 重试（有界）
- **REPORT**：汇总产出 Artifacts（diff、测试报告、风险评估、PR 描述）

### 3.3 模块清单（47 个源文件，14 个包）

| 包 | 职责 | 关键类 |
|----|------|--------|
| `repopilot` (根) | 入口、配置、模型、工作流 | `Config`, `RepairRequest`, `ExecutionMode` |
| `api/` | FastAPI 路由 | `create_app`, `/health` |
| `agents/` | 角色定义与 Prompt 模板 | `AgentRole`, `PlannerDecision` |
| `tools/` | 五类工具实现 | `RealFileTool`, `RealSearchTool`, `RealPatchTool`, `NoopTestRunnerTool`, `RealGitTool` |
| `workflows/` | 状态机与编排器 | `RepairStage`, `RealRepairWorkflowOrchestrator` |
| `runs/` | 运行生命周期管理 | `RunManager`, `RunRecord` |
| `workspace/` | 工作区准备 | `LocalWorkspaceManager` |
| `approvals/` | 审批策略 | `StrictApprovalPolicy` |
| `artifacts/` | 产出构建与持久化 | `ArtifactsWriter` |
| `sandbox/` | 沙箱执行器 | `SubprocessSandboxExecutor` |
| `retrieval/` | 代码检索 | `LocalCodeRetriever` |
| `github/` | GitHub API 边界 | `GitHubClient` (Protocol) |
| `observability/` | 结构化日志 | `TraceEvent` |
| `evaluation/` | 评估合约 | `GoldenCase`, `EvaluationMetric` |

---

## 四、已实现功能（16 个 Feature，全部 Passing）

### 4.1 基础设施

| ID | 功能 | 状态 |
|----|------|------|
| H01 | 新 Agent 可从仓库文件理解项目范围、命令、状态 | ✅ Passing |
| A01 | 生产级架构骨架（CLI/API/模块边界/安全默认值） | ✅ Passing |
| A02 | 分层架构合约（Run/Workspace/Workflow/Agent/Tool/Artifact/Observability/Evaluation） | ✅ Passing |

### 4.2 核心功能

| ID | 功能 | 状态 |
|----|------|------|
| F01 | GitHub Issue URL 或原始描述 → 结构化 RepairRequest | ✅ Passing |
| F02 | 仓库快照 + 文件分类 + 本地关键词检索 | ✅ Passing |
| F03 | 干跑修复工作流（计划 + noop diff + 测试报告 + 风险评估 + PR 描述） | ✅ Passing |
| F04 | 审批门控（补丁/测试执行需显式批准） | ✅ Passing |
| F05 | 沙箱执行模式（DRY_RUN / APPROVED） | ✅ Passing |
| F06 | Subprocess 沙箱执行器（超时、输出捕获、错误处理） | ✅ Passing |

### 4.3 工具层

| ID | 功能 | 状态 |
|----|------|------|
| F07 | RealFileTool — 文件读/写/列表（写操作需审批） | ✅ Passing |
| F08 | RealSearchTool — 关键词 + grep 搜索 | ✅ Passing |
| F09 | RealPatchTool — Unified Diff 应用（通过 `patch` 命令） | ✅ Passing |
| F10 | RealGitTool — git diff/status/log/add/commit（写操作需审批） | ✅ Passing |

### 4.4 端到端流水线

| ID | 功能 | 状态 |
|----|------|------|
| F11 | RealRepairWorkflowOrchestrator — 全阶段驱动 | ✅ Passing |
| F12 | 测试失败反思 + 有界重试循环 | ✅ Passing |
| F13 | ArtifactsWriter — 产出持久化到磁盘 | ✅ Passing |
| F14 | CLI `repopilot run` — 端到端修复命令 | ✅ Passing |

### 4.5 测试覆盖

- **65 个测试用例**，覆盖 11 个测试文件
- 全部离线运行，无网络/GitHub/Docker 依赖
- 单元测试 + 集成测试 + 架构契约测试

---

## 五、Agent 架构设计亮点

### 5.1 确定性编排 vs LLM 推理的职责分离

```
确定性层（控制流）           推理层（决策）
─────────────────         ─────────────────
工作流状态机                补丁生成策略
重试逻辑                   错误根因分析
审批门控                   修复计划优化
工具调度                   PR 描述撰写
```

编排器本身是确定性的——状态转移、重试计数、工具调用顺序全部硬编码。LLM 仅在需要"判断"的节点介入（未来接入）。这种分离确保了：可测试性、可预测性、可审计性。

### 5.2 渐进式替换策略（Noop → Real）

每个子系统都遵循同一模式：

```python
# 1. Protocol 定义接口
class SandboxExecutor(Protocol):
    def run(self, request: CommandRequest, ...) -> CommandResult: ...

# 2. Noop 实现用于早期测试
class NoopSandboxExecutor: ...

# 3. Real 实现替换
class SubprocessSandboxExecutor: ...

# 4. 向后兼容别名
NoopSandboxExecutor = SubprocessSandboxExecutor  # 或保留两者
```

这使得项目可以逐个子系统替换，而不破坏已有测试。

### 5.3 安全优先的工具设计

所有工具共享统一的 `ToolResult` 接口和审批机制：

```python
# 只读操作 — 直接返回
result = git_tool.run({"action": "diff", ...})  # ok=True

# 写操作 — 需要审批
result = git_tool.run({"action": "commit", ...})  # approval_required=True

# 审批后执行
policy.approve(ApprovalSubject.GIT, run_id="...")
result = git_tool.run({"action": "commit", ...})  # ok=True
```

### 5.4 循环依赖规避

`models.py` 中的 `CommandPlan.request` 使用 `Any` 类型而非 `CommandRequest`，避免 `models ↔ sandbox/executor` 的循环导入。这是一个在大型 Agent 系统中常见的模式——数据模型层不应反向依赖执行层。

---

## 六、需要优化的方向

### 6.1 高优先级：LLM 集成（智能补丁生成）

**现状**：补丁生成是占位逻辑，`RealRepairWorkflowOrchestrator` 的 PLAN 阶段产生固定的 dummy diff。

**优化方案**：
- 接入 OpenAI Agents SDK，在 PLAN 阶段调用 LLM 分析 Issue + 代码上下文，生成真实补丁
- 在 FAILURE_ANALYZER 角色中使用 LLM 分析测试失败原因，指导重试策略
- 需要实现 `agents/runner.py`：带重试、限流、token 计量的 LLM 调用层

**影响**：从"模板修复"升级为"智能修复"，是项目核心价值的关键跃迁。

### 6.2 高优先级：GitHub API 集成

**现状**：`NoopGitHubClient` 仅占位，Issue 获取依赖本地 JSON fixture。

**优化方案**：
- 实现 `GitHubAppAuthenticator`（PyJWT + 私钥签名）
- 实现 `RealGitHubClient`：Issue 读取、PR 创建、Review Comment
- 支持 `gh` CLI 作为 fallback（已有 `issue_fetchers.py` 的 Protocol 边界）

**影响**：闭环自动化——从 Issue 入口到 PR 出口全链路打通。

### 6.3 中优先级：Docker 沙箱隔离

**现状**：`SubprocessSandboxExecutor` 直接在宿主机执行命令，无网络隔离、无文件系统隔离。

**优化方案**：
- 实现 `DockerSandboxExecutor`：容器化执行，cgroup 限制 CPU/内存，网络策略隔离
- 挂载目标仓库为只读 volume，补丁通过 stdin 注入
- 超时后强制 kill 容器（而非仅 kill 进程）

**影响**：安全性从"进程级"提升到"容器级"，防止恶意代码逃逸。

### 6.4 中优先级：向量检索增强

**现状**：`LocalCodeRetriever` 基于关键词匹配 + 文件路径评分，无语义理解能力。

**优化方案**：
- 接入 pgvector 或 FAISS，对代码文件做 embedding
- 实现 `SemanticRetriever`：支持自然语言查询（如"authentication retry logic"）
- 检索结果融合：关键词精确匹配 + 语义相似度加权

**影响**：从"关键词搜索"升级为"语义搜索"，提升大仓库中的定位精度。

### 6.5 中优先级：可观测性落地

**现状**：`TraceEvent` 模型已定义，但未在工作流中实际发射事件。

**优化方案**：
- 在编排器每个阶段转换时发射 `TraceEvent`
- 在工具调用前后记录 `TOOL_CALL` 事件（输入摘要、耗时、结果码）
- 接入 OpenTelemetry SDK，导出到 Jaeger/Prometheus
- 添加 `RunRecord.trace_id` 字段，支持端到端链路追踪

**影响**：从"黑盒执行"到"全链路可观测"，是生产环境排障的基础。

### 6.6 低优先级：评估框架

**现状**：`GoldenCase` 和 `EvaluationMetric` 已定义，但无实际评估数据集和运行器。

**优化方案**：
- 构建 SWE-bench Lite 子集作为 golden dataset
- 实现 `EvaluationRunner`：自动化运行 Agent 修复 → 对比 ground truth → 计算指标
- 引入 LLM-as-Judge 评估补丁质量（语义等价性）

**影响**：建立量化反馈循环，驱动 Agent 能力的持续迭代。

### 6.7 低优先级：持久化与并发

**现状**：`RunManager` 是纯内存实现，无持久化；无并发任务支持。

**优化方案**：
- `RunRecord` 持久化到 PostgreSQL
- 引入 Redis 作为任务队列（Celery/Dramatiq worker）
- 支持多 Issue 并行修复

### 6.8 工程质量优化

| 项目 | 当前 | 目标 |
|------|------|------|
| 测试覆盖 | 65 个用例，覆盖主路径 | 补充边界条件、异常路径、并发场景 |
| 错误处理 | 基础 try/except | 统一错误码体系、用户友好的错误消息 |
| 文档 | 架构 + 安全 + 评估 docs | API 文档自动生成、CLI 使用指南 |
| CI/CD | 无 | GitHub Actions：lint → test → build → publish |
| 配置管理 | 环境变量 + pyproject.toml | 支持 YAML/TOML 配置文件、环境差异化 |

---

## 七、架构决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 05-23 | Harness-first 脚手架 | Agent 需要持久化上下文、验证命令、进度状态 |
| 05-23 | 标准库优先 CLI | 最小依赖，clean checkout 即可运行 |
| 05-23 | 窄接口隔离外部集成 | 离线可测试，逐个子系统替换 |
| 05-24 | 审批门控先于执行 | 高风险操作需显式批准边界 |
| 05-27 | ExecutionMode 枚举 | 区分 dry-run 规划与 approved 执行 |
| 05-27 | subprocess 替代 Noop | 首次实现真实命令执行 |
| 05-27 | 渐进式工具替换 | NoopX → RealX，保持测试兼容 |
| 05-27 | 确定性编排器 | 可测试、可预测、可审计 |

---

## 八、总结

RepoPilot v0.1.0 完成了从空目录到端到端可运行的 AI 编程智能体骨架的全部工作：

- **47 个源文件**，14 个包，完整的分层架构
- **16 个 Feature 全部 Passing**，65 个测试用例
- **确定性工作流编排** + 审批门控 + 工具隔离
- **渐进式替换策略**，每个子系统都有 Protocol → Noop → Real 的升级路径
- **完整的产出链路**：diff.patch / test_report / risk_assessment / PR description

下一步的关键跃迁是 **LLM 集成**（智能补丁生成）和 **GitHub API 集成**（闭环自动化），这两项将把 RepoPilot 从"骨架"变为"生产可用的 AI 程序员助手"。
