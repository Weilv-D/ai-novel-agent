# AI Novel Agent - 当前状态

最后更新：2026-03-14

## 仓库健康度

- 后端测试：`395` collected / `393 passed` / `2 skipped`
- 前端校验：`npm run build` 通过，`npm run lint` 通过
- 后端 lint：`ruff check app tests` 通过
- 后端类型检查：`mypy app` 通过
- 后端可编辑安装已修复，`pip install -e ".[dev]"` 可用
- 仓库级验证命令：`make verify`

## 已实现范围

### 后端

- FastAPI 主应用、异常处理、配置与日志
- 单用户个人模式：
  - 固定个人用户身份
  - 启动时自动补齐用户记录
  - 可选 `ADMIN_API_KEY` 访问保护
- SQLAlchemy 模型：
  - `User`
  - `Project`
  - `Character`
  - `WorldSetting`
  - `Volume`
  - `Chapter`
  - `Scene`
  - `Suggestion`
  - `Dependency`
  - `Snapshot`
  - `Memory`
- API 路由：
  - Projects
  - Characters
  - WorldSettings
  - Volumes / Chapters / Scenes
  - Suggestions
  - Dependencies
  - Snapshots
  - Memories
  - Agent chat / stream / auto summarize / continuity check
  - Export
- Alembic 初始化迁移
- LLM service：
  - chat generate
  - stream
  - embeddings
  - retry / health check

### 前端

- Next.js 15 App Router
- 项目、人物、章节、场景、世界观页面
- Suggestion / Diff / Impact Analysis 组件
- API client、store、类型定义
- 首页个人模式设置面板（浏览器本地 API Key 保存）

## 环境现状

当前仓库内与开发相关的本地环境有：

- `backend/.venv`：有效 Python 环境
- `frontend/node_modules`：有效 Node 环境
- `backend/.env`：后端本地配置
- `backend/.env.example`：后端示例配置
- `frontend/.env.local`：前端本地配置

已识别并清理的遗留/生成物方向：

- 仓库根目录 `/.venv`：遗留空壳，不参与项目运行
- `frontend/.next`：前端构建产物
- `__pycache__` / `.pytest_cache` / `.ruff_cache`：缓存目录

## 仍然存在的明确缺口

- 多用户认证/权限体系未实现；当前明确定位为个人单用户应用
- PostgreSQL + pgvector 的完整运行时联调未在本次整理中重跑

## 推荐开发入口

见 [开发说明](DEVELOPMENT.md)。
