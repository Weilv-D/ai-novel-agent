# 当前技术实现说明

最后更新：2026-03-17
文档状态：已按当前仓库代码、测试结果与运行命令核对

## 1. 校验基线

本文件描述“当前已经实现并验证过”的系统行为，不描述未来规划。

本轮核验基线：

- 后端：`cd backend && ./.venv/bin/python -m pytest --cov=app --cov-report=term-missing` -> `541 passed`
- 后端 statement 覆盖率：`90%`
- 前端 lint：`cd frontend && npm run lint` -> 通过
- 前端 type-check：`cd frontend && npm run type-check` -> 通过
- 前端 build：`cd frontend && npm run build` -> 通过
- E2E：`npm run e2e` -> `7 passed`
- OpenAPI 快照：本地 `app.openapi()` 输出 `66` 条路径、`92` 个 schema

## 2. 系统定位与边界

AI Novel Agent 当前定位为“个人长篇创作 Agent 工作台”，服务单实例使用场景。

明确边界：

- 不实现多用户账号体系
- 不实现组织/团队级权限模型
- 访问控制保留为实例级 `ADMIN_API_KEY`
- Redis、PostgreSQL/pgvector 是运行时依赖；SQLite 仅用于测试和 E2E

## 3. 运行拓扑

```text
Next.js Frontend
    |
    v
FastAPI /api/v1
    |
    +--> Domain Services / Agent Workflow
    |        |
    |        +--> OpenAI-compatible Chat / Embedding APIs
    |
    +--> PostgreSQL + pgvector
    |
    +--> Redis
```

## 4. 后端落地

目录分层：

- `backend/app/api/v1/`：HTTP 路由与协议入口
- `backend/app/services/`：业务逻辑与 Agent 工作流
- `backend/app/models/`：SQLAlchemy 持久化模型
- `backend/app/schemas/`：Pydantic contract
- `backend/app/core/`：配置、缓存、日志、异常、安全
- `backend/app/db/`：数据库连接与初始化

当前后端能力面：

- CRUD：Project、Character、WorldSetting、Volume、Chapter、Scene
- 衍生对象：Suggestion、Dependency、Snapshot、Memory
- Agent：thread / run / operation / subtask / checkpoint 工作流
- Export：TXT、Markdown、DOCX、项目包导出/导入
- Runtime：Redis 缓存、pgvector 相似检索、SSE 流式响应
- Timeline：章节顺序 + episode 记忆聚合

### 4.1 Agent 工作流

主流程：

1. 创建或获取项目默认线程
2. 提交消息，生成 run 计划与 preview
3. 普通写入确认执行；高风险正文覆盖触发二次确认
4. 执行 CRUD / 内容写入
5. 通过 verification gate 后完成 run

当前显式 contract：

- `risk_summary`
- `execution_contract`
- `verification_status` / `verification_summary`
- `compact_policy` / `planner_window` / `retained_window` / `active_bundle_contract`

### 4.2 存储与缓存

- PostgreSQL 为主数据库
- `pgvector` 用于 `Memory.embedding`
- SQLite 在测试与 E2E 环境下回退为 JSON 文本向量
- Redis 用于：
  - LLM 非流式响应缓存
  - 向量检索结果缓存

### 4.3 导出与内容形态

- `Project.story_outline -> Volume.outline -> Chapter.outline -> Scene/正文`
- 章节与场景编辑页已支持 TipTap 富文本；内容字段可存 HTML
- TXT / Markdown / DOCX 导出会清理 HTML 标签后输出文本结构

## 5. 前端落地

技术栈：

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS
- Zustand
- TipTap 2.x
- `@dnd-kit/*`
- `@xyflow/react`

当前页面与交互能力：

- 项目详情页内 `AgentWorkspace`
- 人物、设定、卷、章节、场景完整管理页
- 富文本编辑器 + 选中文本内联 AI 改写
- 章节/场景拖拽排序
- 人物关系图谱与依赖图谱
- 时间线视图
- 导出、项目包导入/导出

## 6. 当前质量结论

当前代码基线可认为“功能完整、回归稳定”，但仍存在两类未闭环项：

- 覆盖率未达到 95% 目标，当前为 90%
- 正式的双人方案评审流程未执行；当前仓库验证以单人/AI 审查为主

## 7. 与历史文档的关系

- 产品目标：见 [`../product/PRD.md`](../product/PRD.md)
- 目标架构：见 [`./TECH_ARCH.md`](./TECH_ARCH.md)
- 开发部署：见 [`../development/DEVELOPMENT.md`](../development/DEVELOPMENT.md)
- API：见 [`../api/API_REFERENCE.md`](../api/API_REFERENCE.md)
- QA：见 [`../qa/STATUS.md`](../qa/STATUS.md)
