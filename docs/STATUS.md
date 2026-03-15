# 项目状态

最后更新：2026-03-15

## 当前已完成

AI Novel Agent 当前已经具备可用的个人单用户创作工作流，主交互模型明确为项目内 Agent Workspace，而不是旧的 suggestion 导向聊天面板。

当前稳定能力包括：

- 项目、人物、世界观、卷、章、场景的完整 CRUD
- Snapshot、Memory、Dependency、导出能力
- 项目级 `thread / run / operation` Agent 工作流
- preview-first、confirm-then-execute 的执行模式
- 项目级 `agent_profile_id`
- 内置 `default` 与 `xianxia_intrigue` profile
- profile-aware planner / operation skills
- run 级 subtask 摘要
- run 级 subtask recovery / failure boundary
- run 级 subtask child execution trace
- run 级 hook trace
- run 级 Plan / Build 权限矩阵
- researcher 内部 read/search 工具层
- 显式 `execution_contract` / `child_trace` 接口字段
- capability execution record
- capability registry / policy layering
- operation 风险分级与高风险二次确认
- run 级 risk summary
- risk policy registry / applied policy snapshot
- replaceable risk classifier service
- profile-aware risk classifier override
- explicit child unit contract
- independent execution contract assembly layer
- 执行后 verification gate
- create/update field-level verification
- snapshot semantic verification
- content transition verification
- 长线程 checkpoint 基础设施
- 工作台可见的 latest checkpoint 摘要

## 当前质量状态

- 后端测试：`431 passed / 2 skipped`
- 后端 lint：通过
- 后端类型检查：通过
- 前端 lint：通过
- 前端 build：通过

当前仓库可以通过：

- `ruff check app tests`
- `mypy app`
- `pytest`
- `npm run lint`
- `npm run build`

## 当前边界

以下内容仍不在当前交付范围内：

- 多用户注册、登录、组织与权限体系
- 浏览器自动化 e2e 测试
- 真正独立执行的内部子代理
- 面向公网部署的完整安全加固方案

这些边界是当前产品定位与当前实施顺序的一部分，不是遗漏说明。

## 下一阶段

后续工作不再推翻现有 `thread / run / operation` 底座，而是沿着以下方向收口：

- 把 subtask 从“摘要记录”升级为真正独立的内部执行单元
- 把当前 `Plan / Build` 权限矩阵进一步收敛为明确的 child unit contract
- 把 field-level verification 从当前的 create/update 扩展到更广的对象类型与更细粒度结果
- 把 snapshot semantic verification 与 content transition verification 推进到更细的 domain-level 语义校验
- 把 checkpoint 从基础摘要升级为长期线程的正式 compact 流程

详细路线见 [IMPLEMENTATION_PLAN.md](/home/weilv/workspace/prjforfun/ai-novel-agent/docs/IMPLEMENTATION_PLAN.md)。
