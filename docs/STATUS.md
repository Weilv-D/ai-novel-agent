# 项目状态

最后更新：2026-03-16

## 交付定位

AI Novel Agent 当前定位为独立实例的 Agent 化小说创作工作台。它已经具备完整的本地创作闭环：项目管理、结构化内容维护、Agent 规划与执行、风险控制、落库校验、长期线程压缩、项目包导出导入，以及与这些能力对应的前端工作台。

当前状态适合个人长期使用，也适合作为继续演进 Agent 工作流的稳定基线。

## 当前能力面

### 创作对象

- 项目
- 人物
- 世界观
- 卷、章、场景
- Snapshot、Dependency、Memory、Suggestion、Export
- 项目包导出导入

### Agent 工作流

- 项目级 `thread / run / operation`
- preview-first、confirm-then-execute
- 项目级 profile
- 文件化 planner / operation skills
- 风险摘要与高风险二次确认
- execution contract、child unit contract、capability record
- hook trace、subtask trace、checkpoint trace
- 流式事件系统（SSE）

### 执行保障

- 字段级校验
- snapshot linkage 与 snapshot-derived semantic 校验
- content transition 校验
- domain-level semantic 校验
  - Character: 名称非空、名称唯一、年龄非负
  - WorldSetting: 名称非空、内容非空、同分类名称唯一
  - Chapter/Scene: 章节序号唯一、场景序号唯一
- checkpoint-based compact flow
- planner window、retained window、active bundle contract

### 前端工作台

- 项目页内 Agent Workspace
- run 计划预览
- diff 展示
- 风险与确认面板
- verification 与 compact contract 展示
- 项目、人物、设定、章节、场景的辅助编辑页
- 项目包导出与导入入口
- 宣纸水墨风格 UI（WCAG 2.1 AA 级对比度）

### E2E 测试

- Playwright 测试框架
- Fixture planner 模式（无真实 LLM 依赖）
- 关键节点 data-testid
- 首批用例覆盖核心流程

## 质量状态

当前仓库质量门如下：

- 后端 `ruff check app tests scripts`
- 后端 `mypy app`
- 后端 `pytest`
- 前端 `npm run lint`
- 前端 `npm run build`
- E2E `make e2e`

当前实测结果：

- 后端测试：`441 passed` ✅
- 后端 lint：通过 ✅
- 后端类型检查：通过 ✅
- 前端 lint：通过 ✅
- 前端构建：通过 ✅

## 交付边界

以下内容不属于当前交付范围：

- 多实例协作、组织和权限体系
- 真正独立运行的内部 child agent session
- 面向公网部署的完整安全加固

这些边界来自产品定位和实施顺序，不是已知缺口。

## 架构成熟度

当前系统在以下方面已经形成稳定接口和清晰分层：

- Profile / Skill：项目级绑定与运行期可见性
- Risk：policy registry、applied policy、run risk summary
- Execution：phase、child unit、capability execution record
- Verification：字段、快照、内容迁移、业务语义
- Compact：checkpoint、planner window、retained window、active bundle contract
- Export/Import：项目包导出导入、embedding 维度兼容

这意味着前端、测试和脚本不再依赖解析非结构化 `meta` 来理解 Agent 行为。

## 演进方向

项目后续扩展应优先保持现有 contract 稳定，再继续推进以下方向：

- 把内部 child unit 继续升级为更独立的执行单元
- 扩展 domain-level semantic verification 到更多对象和业务规则
- 细化 compact policy、retained window 和 active bundle 策略
- 在不改变当前主流程的前提下，继续增强 profile 与 skill 体系

详细规划见 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)。
