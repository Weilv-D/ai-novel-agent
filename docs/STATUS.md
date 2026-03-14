# 项目状态

最后更新：2026-03-15

## 当前定位

AI Novel Agent 已经具备可用的个人创作工作流，不再是原型阶段。它当前服务的对象很明确：单人、本地、长期创作。项目的设计重点是稳定的内容结构和 AI 辅助链路，而不是多用户协作系统。

## 已交付能力

### 后端

- FastAPI 主应用与异常处理
- 配置、日志与健康检查
- 单用户模式与可选 `ADMIN_API_KEY` 保护
- 项目、人物、世界观、卷、章、场景的完整 API
- Suggestion、Dependency、Snapshot、Memory 相关 API
- Agent chat / stream / continuity / summarize
- Alembic 初始化迁移
- PostgreSQL + pgvector 目标运行时

### 前端

- Next.js 15 App Router
- 首页与个人模式配置入口
- 项目、人物、章节、世界观主视图
- Suggestion / Diff / Impact Analysis 组件
- API client、状态管理与类型定义
- 当前版本的水墨风 UI 主题

### 运行与验证

- 仓库级验证命令：`make verify`
- 后端快速验证：`backend/verify.py`
- SQLite HTTP 集成验证：`scripts/verify_sqlite_integration.py`
- 联调环境 live smoke：`scripts/verify_api_integration.py`
- Docker Compose 本地联调可用

## 当前质量状态

- 后端测试：`398` collected / `396 passed` / `2 skipped`
- 后端 lint：通过
- 后端类型检查：通过
- 前端 lint：通过
- 前端 build：通过
- 健康接口：返回 API、数据库和 Redis 的实时状态

## 当前边界

以下内容不在当前交付范围内：

- 多用户注册、登录、组织与权限体系
- 浏览器自动化 e2e 测试
- 面向公网部署的完整安全加固方案

这些边界是当前产品定位的一部分，而不是遗漏。

## 维护建议

- 把 `make verify` 作为提交前最低验证标准
- 把 `/api/v1/health` 作为联调环境启动后的第一道检查
- 修改 embedding 模型时，同步调整 `EMBEDDING_DIMENSION`
- 保持 `frontend/.next-docker` 只作为 Docker 前端运行态目录使用
