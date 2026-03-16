# Agent Workflow 演进计划

最后更新：2026-03-16

## 文档目的

本文档给出 Agent Workflow 的长期演进顺序。它不重复描述已经落地的全部实现细节，而是定义：

- 当前基线不变的约束
- 后续扩展的优先级
- 各主题的验收标准

当前系统已经具备完整可用的独立实例创作闭环。下面的计划用于控制未来扩展方向，避免破坏现有 contract。

## 当前基线

以下约束视为稳定基线：

- 主流程是项目级 `thread / run / operation`
- 主交互入口是项目详情页内的 `AgentWorkspace`
- 写入遵循 preview-first、confirm-then-execute
- 高风险正文覆盖需要二次确认
- 执行完成前必须经过 verification gate
- 长线程上下文通过 checkpoint compact flow 管理
- Profile / Skill、Risk、Execution、Verification、Compact 都以显式 contract 对外暴露

## 规划原则

后续演进遵循这些原则：

- 保持公开 contract 稳定
- 优先增强内部层次，而不是增加无约束的功能面
- 先保证可解释性，再增加自动化程度
- 新能力应复用现有 CRUD、snapshot、risk 和 verification 基础设施

## 主题一：Profile 与 Skill 体系

### 目标

让项目级 profile 成为稳定的策略入口，而不是一次性的 prompt 选择器。

### 当前基线

- 项目支持 `agent_profile_id`
- 内置 `default` 与 `xianxia_intrigue`
- `AGENT_SKILLS_DIR` 可覆盖 profile 根目录
- 运行期可查看 profile / skill catalog

### 规划方向

- 为 profile 建立更清晰的 reference catalog
- 在保持当前加载模型的前提下增加更多风格 profile
- 为 profile 切换定义更严格的兼容策略和运行期说明

### 验收标准

- 新 profile 不破坏现有 project-level binding
- skill catalog 仍能按项目返回真实生效结果
- 历史 run 的 profile snapshot 保持稳定可追溯

## 主题二：内部执行层

### 目标

把当前显式 child unit contract 继续推进成更独立的内部执行结构。

### 当前基线

- `planner / researcher / writer / editor / continuity / executor` 已显式建模
- subtask、child trace、recovery boundary、hook trace 已可见
- child unit 仍在 workflow 内部执行

### 规划方向

- 细化各角色的输入输出 schema
- 把 trace 推进为更完整的 execution record
- 在不破坏现有 run contract 的前提下提高 child unit 独立性

### 验收标准

- child unit contract 继续保持显式字段
- workflow service 不重新退回到单块 prompt 编排
- 内部失败边界和重试边界可独立观察

## 主题三：权限与风险

### 目标

保持 Plan / Build 分层清晰，并继续强化 capability policy。

### 当前基线

- `read/search` 只在内部 capability 层自动执行
- `standard_write` 需要一次确认
- `high_risk_write` 需要二次确认
- risk policy registry、applied policy 和 run risk summary 已稳定

### 规划方向

- 丰富 capability policy，而不改变当前 run 风险 contract
- 让 profile 对风险策略的影响继续保持可解释和可追踪
- 提升高风险正文操作的分类精度

### 验收标准

- `risk_summary` 结构保持稳定
- 前端不需要根据 operation 列表自行推断整体风险
- 高风险分类可通过 registry 和 applied policy 解释

## 主题四：Verification Gate

### 目标

继续强化“计划正确”和“落库正确”的一致性保证。

### 当前基线

- 已有字段级、snapshot、content transition、domain semantic 校验
- run 只有在通过 verification gate 后才会完成

### 规划方向

- 将 domain-level semantic verification 扩展到更多对象和更细粒度业务规则
- 细化 create / update / write 的差异化验证策略
- 为需要人工复核但无需失败的结果提供更明确的分类

### 验收标准

- verification contract 继续显式、稳定
- 新的语义校验不会破坏现有已通过链路
- 故障用例能区分字段错误、快照错误、内容迁移错误和业务语义错误

## 主题五：长期线程与压缩

### 目标

让长期线程在可解释前提下持续可用。

### 当前基线

- checkpoint 已持久化
- planner 已支持 `recent_window` 和 `checkpoint_delta`
- compact policy、planner window、retained window、active bundle contract 已显式返回

### 规划方向

- 细化 retained window 规则
- 细化 active bundle 选择策略
- 增加更明确的压缩可追踪说明

### 验收标准

- compact contract 保持稳定
- planner 输入边界始终可解释
- 前端和测试不需要解析非结构化 metadata

## 公共接口约束

以下接口与结构视为公开稳定面：

- `Project.agent_profile_id`
- `AgentThread / AgentRun / AgentOperation`
- `execution_contract`
- `risk_summary`
- `verification_status / verification_summary`
- `compact_policy / planner_window / retained_window / active_bundle_contract`
- checkpoint 响应中的 compact contract

未来扩展应以增量字段和新增接口为主，不推翻这些核心结构。

## 质量门

Agent Workflow 相关变更至少应保持以下命令通过：

- `ruff check app tests scripts`
- `mypy app`
- `pytest`
- `npm run lint`
- `npm run build`

## 参考模式

后续演进继续借鉴这些实现思路：

- Claude Code：子代理、hook、上下文与权限边界
- OpenCode：Plan / Build 分层、child session、permission matrix
- OpenClaw：长期线程隔离、session pruning、workflow / skills

借鉴的重点是编排方式和上下文治理，而不是照搬其产品交互形态。
