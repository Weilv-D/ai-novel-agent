# Agent Workflow 实施路线图

最后更新：2026-03-15

## 当前基线

当前仓库已经把 Agent 主流程稳定在 `thread / run / operation` 这一层，不再回到旧的“单一大 prompt + suggestion 状态机”。

当前已落地的公共工作流是：

1. 项目级默认 `AgentThread`
2. 用户消息生成一个 `AgentRun`
3. `AgentRun` 先返回可见的 operation 预览
4. 用户确认后再执行写入
5. 执行前创建 snapshot
6. 执行后经过 verification gate 才能进入 `completed`

本轮已经补上的基础能力：

- 项目级 `agent_profile_id`
- 内置 `default` 与 `xianxia_intrigue` 两个 profile
- profile-aware skill registry
- `AgentSubtask`
- `AgentThreadCheckpoint`
- operation 风险分级与二次确认
- run / operation verification 字段
- 长线程压缩的 checkpoint 基础设施
- 前端项目创建、编辑、工作台对 profile / risk / verification / subtask 的可见支持

## 目标工作流

目标不是“聊天后给一段建议”，而是“项目内的可验证 Agent 执行系统”。

完整目标流程如下：

1. 用户在项目工作台提出自然语言指令
2. 系统按项目级 profile 装配技能与上下文
3. planner 生成用户可见 operations 与内部 subtasks
4. 前端展示计划、风险等级、diff 预览与内部执行摘要
5. 用户完成一次或两次确认
6. executor 复用现有 CRUD service 落库
7. verification gate 校验落库结果与预览一致
8. 长线程在阈值到达后生成 checkpoint，后续规划改用压缩上下文

## 分阶段计划

### Phase 1: 项目级 Skill Profile

目标：把 skill 选择从“全局默认”提升到“项目级绑定”。

当前实现：

- `Project.meta.agent_profile_id` 已启用
- 新建/编辑项目可以选择 profile
- 内置 profile：
  - `default`
  - `xianxia_intrigue`
- `xianxia_intrigue` 的 planner 与 operation skills 已直接引用 `others/大纲设计提示词.txt`、`others/章纲细纲设计提示词.txt`、`others/写作提示词.txt`
- `GET /api/v1/agent/profiles` 已可用
- `GET /api/v1/agent/skills?project_id=...` 已按项目返回有效 profile

后续收口：

- 为 profile 增加更细的 reference catalog，而不只是 skill 列表
- 允许 `AGENT_SKILLS_DIR` 以 profile 根目录方式覆盖单个 profile
- 增加更多风格 profile 前，先把 profile 选择和迁移约束写清楚

### Phase 2: 内部子代理与 Hook 编排

目标：从单个 planner 演进到内部可编排的多角色执行层。

当前实现：

- `AgentSubtask` 已持久化
- 工作台已展示 planner / researcher / writer / editor / continuity 摘要
- 每个角色的 subtask unit 已有独立的服务端合成逻辑
- planner 如果提供了不合法的 subtask，系统会按角色回退到服务端安全版本
- unrecoverable 的 subtask unit 会在 blueprint 阶段直接拒绝，不会生成可执行 run
- 每个 subtask 已带出 child execution trace，记录依赖、输入摘要、重试策略与尝试结果
- `PrePlan` 等价能力已经存在于 workflow service：
  - profile 选择
  - context bundle 装配
  - subtask 合成
- run metadata 已记录 `PreCompact / PrePlan / SubagentStop / RunStop` hook trace
- `RunStop` 的基础语义已经落在 verification gate
- `PreCompact` 的基础语义已经落在线程 checkpoint

后续收口：

- 把 planner、writer、editor、continuity 从“服务端合成 + child trace”的内部层升级为真正独立的 child execution unit
- 给每个 subtask 建立更完整的输入/输出 schema，并把当前 trace 升级为可重放的执行记录
- 明确 hook 生命周期：
  - `PrePlan`
  - `SubagentStop`
  - `RunStop`
  - `PreCompact`

### Phase 3: 权限分级与确认模型

目标：把所有写入从统一确认，升级为按风险分层确认。

当前实现：

- operation 已带有：
  - `permission_level`
  - `risk_level`
  - `requires_secondary_confirmation`
- run metadata 已带出 `Plan / Build` 权限矩阵
- `researcher` 子任务已切到内部 `read/search` 工具层，不再把这类能力暴露成用户可确认 operation
- `AgentRunResponse.execution_contract` 与 `AgentSubtaskResponse.child_trace` 已成为显式响应字段
- `execution_contract.capabilities[*].execution_record` 已记录 capability 的真实执行状态与输出摘要
- capability 已分成 `registry / policy / execution_record` 三层，`GET /api/v1/agent/capabilities` 可独立查看 registry
- 风险分类已分成 `registry / applied_policies / run summary` 三层，`GET /api/v1/agent/risk-policies` 可独立查看 registry
- 风险分类实现已从 workflow 内部规则提取为独立 classifier service，当前入口是 `app/services/agent_risk.py`
- classifier 已支持 profile-aware override，当前 `xianxia_intrigue` 会使用更保守的长正文覆盖阈值，同时保持原有 risk policy contract 不变
- `AgentRunResponse.risk_summary` 已提供稳定的 run 级风险聚合与命中策略，前端不再需要从 operation 列表和 run 状态机自行推断整体风险
- `execution_contract.phases[*].child_units` 已把 `planner / researcher / writer / editor / continuity / executor` 收敛为显式 child unit contract
- phase contract 与 child unit contract 的装配已提取到独立服务，当前入口是 `app/services/agent_contract.py`
- run 状态机已扩展出 `awaiting_high_risk_confirmation`
- `POST /api/v1/agent/runs/{run_id}/confirm-high-risk` 已可用
- 前端已展示高风险提示与二次确认入口

当前分级规则：

- `standard_write`：普通创建、更新、续写
- `high_risk_write`：长文本覆盖或多对象正文重写

后续收口：

- 继续把 Plan / Build 权限边界推进成可复用的 child capability policy，而不是只停留在 run 级 contract

### Phase 4: 完成校验与落库一致性

目标：不允许 run 在“实际没写对”的情况下标记为成功。

当前实现：

- `AgentRun` / `AgentOperation` 已有：
  - `verification_status`
  - `verification_summary`
- 内容型 operation 已记录：
  - `preview_content_hash`
  - `persisted_content_hash`
- `create_*` 与非正文类 `update_*` 已接入字段级 verification，会按 payload 对落库结果逐字段比对
- operation 的 `execution_result` 已记录 snapshot linkage，verification 会校验 snapshot 是否真实存在、与目标对象一致，并验证从 snapshot 推导出的预期落库状态是否成立
- `write_*_content` 已接入 content transition verification，会验证 replace / append 模式下的正文迁移是否符合预期
- chapter / scene 已接入 domain-level semantic verification，会校验章节序号、场景序号、卷归属与 POV 人物归属这类业务约束
- 长线程已经切换到 checkpoint-based compact flow；当 checkpoint 可用时，planner history 改为 `checkpoint + delta history`，而不是继续读取固定窗口历史
- 执行完成后会验证：
  - 目标对象存在
  - 摘要与预览一致
  - 内容 hash 与 planning 阶段一致
  - create/update 字段与预期值一致
  - snapshot linkage 与 snapshot-derived semantics 有效
  - content transition 与 write mode 语义一致
  - 领域约束与对象归属一致
  - continuity gate 未阻断

后续收口：

- 把当前字段级 verification 从 create/update 扩展到更多对象与更细粒度结果
- 把当前 domain-level semantic verification 从章节/场景约束推进到更多对象与更细的业务规则
- 把当前 checkpoint-based compact flow 从 delta history 切换推进到更完整的 compact policy 与 planner input contract
- 在前端提供更清晰的“执行成功但建议人工复核”的分类展示

### Phase 5: 上下文压缩与长期线程

目标：让单项目长期工作线程可以持续运行，而不是历史越长越不可用。

当前实现：

- `AgentThreadCheckpoint` 已持久化
- 压缩触发条件已存在：
  - 消息数阈值
  - run 数阈值
  - 上下文字符总量阈值
- checkpoint 当前保存：
  - `thread_summary`
  - `active_object_bundle`
  - `recent_run_digest`
  - `profile_id`
- planner 已切换到 `checkpoint + delta history` 输入模式；当 checkpoint 可用时，不再继续回灌固定窗口历史
- `PreCompact / PrePlan` hook metadata 已显式记录 compact mode 与 delta history 状态

后续收口：

- 把当前 compact flow 从固定规则推进到更完整的 compact policy
- 把 planner 输入 contract 从当前的 `checkpoint + delta history` 推进到更清晰的 compact policy / retained window / active bundle 约束
- 为 long-running thread 增加压缩后的可追踪性说明

## 公共接口变更

当前已纳入公共接口的新增内容：

- `ProjectCreate / ProjectUpdate / ProjectResponse.agent_profile_id`
- `GET /api/v1/agent/profiles`
- `GET /api/v1/agent/risk-policies`
- `GET /api/v1/agent/skills?project_id=...`
- `POST /api/v1/agent/runs/{run_id}/confirm-high-risk`
- `AgentRunResponse.subtasks`
- `AgentRunResponse.risk_summary`
- `AgentExecutionPhaseResponse.child_units`
- `AgentRunResponse.verification_status`
- `AgentRunResponse.verification_summary`
- `AgentOperationResponse.permission_level`
- `AgentOperationResponse.risk_level`
- `AgentOperationResponse.requires_secondary_confirmation`
- `AgentOperationResponse.verification_status`
- `AgentOperationResponse.verification_summary`

以下接口继续保留为兼容层：

- `/api/v1/agent/chat`
- `/api/v1/agent/chat/stream`
- `/api/v1/agent/auto-summarize`
- `/api/v1/agent/continuity-check`

## 测试门与验收标准

当前最低质量门：

- `ruff check app tests`
- `mypy app`
- `pytest`
- `npm run lint`
- `npm run build`

本轮新增的重点覆盖：

- profile registry 加载与覆盖
- `xianxia_intrigue` profile 的 canonical source 引用
- 项目级 profile round-trip
- skill catalog 按项目返回有效 profile
- 高风险二次确认链路
- subtask recovery / unrecoverable failure 边界
- subtask child execution trace
- run-level permission matrix 与 internal read/search layer
- explicit execution contract / child trace response schema
- capability execution record
- capability registry / policy layering
- run-level risk summary for normal and high-risk plans
- risk policy registry and applied policy snapshots
- replaceable classifier service
- explicit child unit contract inside execution phases
- subtask 与 verification 字段的 API 暴露

## 兼容与迁移策略

- `AgentThread / AgentRun / AgentOperation` 继续视为公共稳定接口，只增量扩展，不推翻重做
- 项目级 profile 继续存储在 `Project.meta`，避免新增数据库列
- legacy chat 与 suggestion 兼容路径继续保留，但不再作为主流程继续扩展
- 新 profile 只影响新 run；历史 run 保留自己的 `profile_id` 与 skill snapshot

## 参考模式

- Claude Code：
  - 子代理
  - hooks
  - 独立上下文与权限边界
- OpenCode：
  - Plan / Build 分层
  - child sessions
  - permission matrix
- OpenClaw：
  - 长线程隔离
  - session pruning
  - workflow / skills 思路

本项目后续主要吸收 Claude Code 与 OpenCode 的编排方式，OpenClaw 主要借鉴长期会话和压缩策略，不照搬其聊天网关形态。
