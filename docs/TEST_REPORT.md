# 测试报告

测试日期：2026-03-16  
测试执行人：AI Agent  
测试环境：

- OS: Linux
- Python: 3.12.3（`backend/.venv`）
- Node.js: 使用仓库当前本地版本
- 数据库：SQLite（测试/E2E），代码目标支持 PostgreSQL + pgvector
- 浏览器：Playwright Chromium

## 1. 测试计划与覆盖范围

覆盖模块：

- API 路由层（`backend/tests/test_api`）
- 服务层（`backend/tests/test_services`）
- Schema 层（`backend/tests/test_schemas`）
- 集成层（`backend/tests/test_integration`）
- 前端静态质量门（lint/build）
- 浏览器 E2E 场景（Agent、导出、导入）

执行结果摘要：

| 维度 | 结果 |
|---|---|
| 后端单元/集成 | `441 passed` |
| 后端覆盖率（statement） | `75%` |
| 前端 lint | 通过 |
| 前端 build | 通过 |
| E2E | `7 passed` |

说明：当前 statement 覆盖率未达到 95% 目标，需后续补测（重点在 `agent_workflow.py`、`project_package.py` 等复杂路径）。

## 2. 关键测试用例清单

| 用例ID | 测试目的 | 前置条件 | 输入数据 | 操作步骤 | 预期结果 | 实际结果 | 状态 |
|---|---|---|---|---|---|---|---|
| TC-AGENT-001 | 创建默认线程并返回线程状态 | 已创建项目 | `project_id` | 调用 `POST /agent/threads` | 返回默认线程对象 | 与预期一致 | 通过 |
| TC-AGENT-002 | 发送消息并生成待确认 run | 已有线程 | `content=创建一个测试人物` | 调用 `POST /agent/threads/{id}/messages` | 返回 run 与 operations | 与预期一致 | 通过 |
| TC-AGENT-003 | 确认执行后写入人物 | 有待确认 run | `run_id` | 调用 `/agent/runs/{id}/confirm` | 人物数据落库，run 完成 | 与预期一致 | 通过 |
| TC-PKG-001 | 项目包导出可下载 | 已有项目 | `project_id` | 调用 `GET /projects/{id}/package` | 返回 zip 流 | 与预期一致 | 通过 |
| TC-PKG-002 | 项目包导入创建副本 | 已有 zip 包 | `file,new_name` | 调用 `POST /projects/import` | 新建副本并返回计数 | 与预期一致 | 通过 |
| TC-EXP-001 | 文本导出正常返回 | 已有项目 | `format=txt` | 调用 `GET /projects/{id}/export` | 返回文本下载 | 与预期一致 | 通过 |
| TC-E2E-001 | 项目创建流程 | 前后端服务可用 | 表单数据 | 浏览器创建项目 | 跳转到详情页 | 与预期一致 | 通过 |
| TC-E2E-002 | Agent 创建人物流程 | fixture 模式开启 | 固定指令 | 浏览器发送指令并确认 | 人物在列表页可见 | 与预期一致 | 通过 |
| TC-E2E-003 | Agent 修改设定流程 | fixture 模式开启 | 固定指令 | 浏览器发送指令并确认 | 设定在列表页可见 | 与预期一致 | 通过 |
| TC-E2E-004 | 高风险正文覆盖流程 | 已存在章节 | 固定指令 | 浏览器确认执行并轮询 API | 章节正文被替换 | 与预期一致 | 通过 |

## 3. 边界与异常覆盖说明

已覆盖的异常/边界方向：

- 缺失或错误鉴权头（401/403）
- 参数校验失败（422）
- 资源不存在（404）
- 业务校验失败（400/409）
- embedding 维度不一致导入 warning
- Agent fixture 缺失配置/路径时失败路径

## 4. 覆盖率结果与差距

本轮覆盖率：

- 语句覆盖率：75%

与目标差距：

- 目标 95%，当前差距 20 个百分点

建议补测优先级：

1. `agent_workflow.py` 复杂分支（多阶段风险、compact、verification 失败路径）
2. `project_package.py` 导入导出异常分支（损坏包、映射缺失、回滚场景）
3. `orchestrator` 与 legacy agent 路由路径

## 5. 回归测试结论

针对本轮修复点（线程并发、项目包导出、导出 UUID、E2E 夹具路径与接口）已完成回归；关键链路通过，未发现新增阻塞问题。
