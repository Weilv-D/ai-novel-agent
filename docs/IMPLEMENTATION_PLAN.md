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
- `PrePlan` 等价能力已经存在于 workflow service：
  - profile 选择
  - context bundle 装配
  - subtask 合成
- run metadata 已记录 `PreCompact / PrePlan / SubagentStop / RunStop` hook trace
- `RunStop` 的基础语义已经落在 verification gate
- `PreCompact` 的基础语义已经落在线程 checkpoint

后续收口：

- 把 planner、writer、editor、continuity 从“带 hook trace 的结构化内部层”升级为真正独立的执行单元
- 给每个 subtask 建立独立 schema 和失败重试边界
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
- run 状态机已扩展出 `awaiting_high_risk_confirmation`
- `POST /api/v1/agent/runs/{run_id}/confirm-high-risk` 已可用
- 前端已展示高风险提示与二次确认入口

当前分级规则：

- `standard_write`：普通创建、更新、续写
- `high_risk_write`：长文本覆盖或多对象正文重写

后续收口：

- 增加真正的 `read_search` 内部工具层，并从用户可见 operation 中剥离
- 把“高风险”从当前规则判断升级到更稳定的 classifier
- 增加批量修改时的 run 级风险摘要

### Phase 4: 完成校验与落库一致性

目标：不允许 run 在“实际没写对”的情况下标记为成功。

当前实现：

- `AgentRun` / `AgentOperation` 已有：
  - `verification_status`
  - `verification_summary`
- 内容型 operation 已记录：
  - `preview_content_hash`
  - `persisted_content_hash`
- 执行完成后会验证：
  - 目标对象存在
  - 摘要与预览一致
  - 内容 hash 与 planning 阶段一致
  - continuity gate 未阻断

后续收口：

- 对非内容字段增加更细的 field-level verification
- 对 snapshot 与 verification 建立明确联动关系
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

后续收口：

- 把当前确定性摘要升级为独立 compact step
- 将 planner 输入正式切换为：
  - 最新 checkpoint
  - 当前关键对象 bundle
  - 少量近期原始消息
  - 当前待确认 run 摘要
- 为 long-running thread 增加压缩后的可追踪性说明

## 公共接口变更

当前已纳入公共接口的新增内容：

- `ProjectCreate / ProjectUpdate / ProjectResponse.agent_profile_id`
- `GET /api/v1/agent/profiles`
- `GET /api/v1/agent/skills?project_id=...`
- `POST /api/v1/agent/runs/{run_id}/confirm-high-risk`
- `AgentRunResponse.subtasks`
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
