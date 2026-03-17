# 当前技术实现说明

最后更新：2026-03-16
文档状态：已按当前仓库代码核对

## 1. 文档范围与校准基线

本文件描述当前仓库已经落地并可运行的真实实现，不描述未来规划。

本次针对“双层规划体系”更新的核对基线：

- 后端回归：`backend/.venv/bin/pytest backend/tests/test_schemas/test_project_schemas.py backend/tests/test_schemas/test_suggestion_schemas.py backend/tests/test_services/test_project_service.py backend/tests/test_services/test_chapter_service.py backend/tests/test_services/test_project_package_service.py backend/tests/test_api/test_projects.py backend/tests/test_api/test_suggestions.py backend/tests/test_api/test_agent_workflow.py backend/tests/test_integration/test_http_integration.py -q` -> `162 passed`
- 前端质量门：`npm run lint --prefix frontend`、`npm run build --prefix frontend` 通过

相关文档：

- API 文档：`docs/API_REFERENCE.md`
- 开发与部署：`docs/DEVELOPMENT.md`
- 逻辑审查：`docs/REVIEW_REPORT.md`
- 测试报告：`docs/TEST_REPORT.md`

## 2. 系统定位与边界

系统定位为“个人长篇创作 Agent 工作台”，核心是项目级数据管理 + Agent 规划执行闭环。

当前边界：

- 不实现多用户账号体系
- 不实现组织级权限隔离
- 业务接口按实例级 `ADMIN_API_KEY` 控制访问

## 3. 运行架构

运行形态：前后端分离单体。

- 前端：Next.js 15 + React 19（App Router）
- 后端：FastAPI + SQLAlchemy 2.x（AsyncSession）
- 数据库：PostgreSQL（主环境），SQLite（测试/E2E）
- 向量：pgvector（SQLite 场景回退 JSON 文本向量）
- 缓存/任务依赖：Redis

请求链路：

1. 前端调用 `/api/v1/*`
2. 路由层注入 DB Session、鉴权依赖
3. Service 层执行业务编排
4. Model 层落库 + 回写响应 schema

## 4. 后端分层实现

- `backend/app/api/v1/`：路由与协议入口
- `backend/app/services/`：业务逻辑与 Agent 编排
- `backend/app/models/`：SQLAlchemy 模型
- `backend/app/schemas/`：Pydantic 协议契约
- `backend/app/core/`：配置、异常、日志、安全
- `backend/app/db/`：连接、session、初始化

## 5. 功能实现现状

### 5.1 创作对象能力

已实现完整 CRUD：

- Project
- Character
- WorldSetting
- Volume
- Chapter
- Scene
- Suggestion
- Dependency
- Snapshot
- Memory（含向量检索）

当前创作层级：

- `Project.summary`：项目简介
- `Project.story_outline`：项目大纲
- `Volume.outline`：卷细纲总述
- `Chapter.title + Chapter.outline`：卷下章纲
- `Scene`：写作执行层

兼容规则：

- 历史项目升级后自动补一个默认卷
- 未挂卷章节自动迁入默认卷
- 旧 `summary / notes` 用于回填 `story_outline`

### 5.2 Agent 工作流

核心模型：

- `AgentThread`
- `AgentMessage`
- `AgentRun`
- `AgentOperation`
- `AgentSubtask`
- `AgentThreadCheckpoint`

主流程（preview-first）：

1. `POST /agent/threads` 创建或获取项目默认线程
2. `POST /agent/threads/{thread_id}/messages` 生成计划（不落主业务数据）
3. 用户确认：`/agent/runs/{run_id}/confirm`
4. 需要二次确认时：`/confirm-high-risk`
5. 执行后写入对象、快照、验证结果

风险控制现状：

- 确认门禁是“按操作和策略动态决定”
- 非所有改写都需要二次确认
- 长文本覆盖（超过策略阈值）或多对象联动重写才进入双确认门禁

当前可写操作集合已扩展为：

- `update_project_outline`
- `create_volume`
- `update_volume`
- `create_character`
- `update_character`
- `create_world_setting`
- `update_world_setting`
- `create_chapter`
- `update_chapter`
- `write_chapter_content`
- `create_scene`
- `update_scene`
- `write_scene_content`

Planner 读取顺序已改为优先使用：

1. 项目大纲
2. 当前卷细纲
3. 卷下章节顺序与章纲
4. 相关人物与世界观

### 5.3 项目包导出/导入

接口：

- `GET /projects/{project_id}/package`
- `POST /projects/import`

打包结构：

- `manifest.json`
- `project_bundle.json`

导入特性：

- 全量新建副本，不覆盖原项目
- 重新生成主键并维护引用映射
- embedding 维度不一致时清空向量并返回 warning
- 项目包版本已提升到 `1.1.0`
- 项目包包含 `story_outline`，导入时会校验卷/章层级并回填缺失项目大纲

### 5.4 文本导出

接口：

- `GET /projects/{project_id}/export?format=txt|markdown`

返回：

- `text/plain` 或 `text/markdown` 下载流

### 5.5 E2E Fixture Planner

通过环境变量启用：

- `AGENT_E2E_MODE=fixture`
- `AGENT_E2E_FIXTURE_PATH=../e2e/fixtures`

在该模式下，规划器直接读取 `planner-responses.json`，不调用真实 LLM。

## 6. 近期关键修复（已合入代码）

1. `project_package` 导出逻辑不再依赖不存在的 ORM relationship，改为按 `project_id` 显式查询各表。
2. `project_package` 序列化改为 mapper 属性级读取，修复 `metadata` 字段序列化异常。
3. `agent_workflow` 默认线程创建加入并发冲突兜底，避免 `unique_default_agent_thread` 竞态失败。
4. 导出接口 `project_id` 改为 `UUID` 类型，修复 SQLite 下字符串 UUID 绑定失败。
5. E2E 夹具接口路径同步到当前 API（去除旧的 `/projects/{id}/...` 风格）。
6. Playwright fixture 路径与导入流程修复，E2E 全量通过。

## 7. 业务流程说明

### 7.1 标准创建流程（项目大纲/卷细纲/章纲）

1. 用户在项目页发送自然语言指令
2. Agent 产出 operation 计划与风险摘要
3. Planner 根据项目大纲、卷细纲、章纲与上下文装配计划
4. 用户确认后落库
5. 系统写 snapshot 与 verification
6. 前端回显当前 run 结果与 recent runs

### 7.2 异常流程

- 资源不存在：`404`
- 参数不合法：`422`（FastAPI 校验）或 `400`（业务校验）
- 唯一性冲突：`409`
- 外部模型不可用：`503`

## 8. 非功能实现说明

### 8.1 性能

- 前端支持骨架屏、去抖/节流 hooks、渐进式加载
- Agent 长线程通过 checkpoint + compact policy 控制上下文规模
- E2E 与测试默认使用 SQLite，生产建议 PostgreSQL + pgvector

### 8.2 安全

- 实例级 API Key 校验（`X-API-Key`）
- 后端集中异常处理，避免直接泄露堆栈
- 仍需在生产环境补充网关、限流、审计与密钥轮换

### 8.3 兼容性

- 主运行目标：Linux + Python 3.11+/Node 18+
- SQLite 为兼容测试环境保留，不作为生产主数据库方案

## 9. 已知限制

- 后端总体覆盖率目前为 75%，未达到 95% 目标
- Agent 子角色仍为单服务内编排，不是独立子会话执行体
- 公开部署场景未内建租户隔离能力

## 10. 验证结论

基于当前代码与本次回归结果，项目大纲、卷细纲、章纲、Agent 计划执行与导出导入链路可用，文档已同步到当前实现状态。后续优先级应放在覆盖率提升与生产级安全加固。
