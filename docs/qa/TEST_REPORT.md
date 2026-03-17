# 测试报告

最后更新：2026-03-17

## 1. 测试环境

| 维度 | 信息 |
| --- | --- |
| 操作系统 | Linux |
| Python | 3.12.3 |
| Node.js | 仓库本地 Node 运行环境 |
| 后端数据库 | SQLite（测试/E2E）、PostgreSQL 设计目标 |
| 浏览器 | Playwright Chromium |
| 代码基线 | `master` 当前工作树 |

## 2. 执行命令

```bash
# 后端全量回归 + 覆盖率
cd backend && ./.venv/bin/python -m pytest --cov=app --cov-report=term-missing

# 前端质量门
cd frontend && npm run lint
cd frontend && npm run type-check
cd frontend && npm run build

# E2E
npm run e2e
```

## 3. 结果摘要

| 维度 | 结果 | 状态 |
| --- | --- | --- |
| 后端 pytest | `541 passed` | 通过 |
| 后端 statement 覆盖率 | `90%` | 未达目标 |
| 前端 lint | 通过 | 通过 |
| 前端 type-check | 通过 | 通过 |
| 前端 build | 通过 | 通过 |
| Playwright E2E | `7 passed` | 通过 |

说明：

- 分支覆盖率当前未配置独立统计，无法给出可信的 branch coverage 数字
- `95%+` 目标当前仅部分达成：功能回归通过，但覆盖率仍为 `90%`

## 4. 核心测试用例矩阵

| 用例ID | 目的 | 前置条件 | 输入 | 步骤摘要 | 预期结果 | 实际结果 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `TC-PROJ-001` | 创建项目 | 服务可用 | 基础项目数据 | 创建项目并跳转详情页 | 返回项目详情 | 与预期一致 | 通过 |
| `TC-PROJ-002` | 更新项目大纲 | 已有项目 | `story_outline` | PATCH 项目 | 大纲更新成功 | 与预期一致 | 通过 |
| `TC-VOL-001` | 创建卷 | 已有项目 | 卷数据 | POST volume | 返回卷对象 | 与预期一致 | 通过 |
| `TC-CH-001` | 创建章节 | 已有项目/卷 | 章节数据 | POST chapter | 返回章节对象 | 与预期一致 | 通过 |
| `TC-CH-002` | 章节重排 | 同卷多章 | 章节 ID 顺序 | POST reorder | 顺序持久化 | 与预期一致 | 通过 |
| `TC-SC-001` | 场景重排 | 同章多场景 | 场景 ID 顺序 | POST reorder | 顺序持久化 | 与预期一致 | 通过 |
| `TC-CHAR-001` | 创建人物 | 已有项目 | 人物数据 | POST character | 返回人物对象 | 与预期一致 | 通过 |
| `TC-WS-001` | 创建设定 | 已有项目 | 设定数据 | POST world-setting | 返回设定对象 | 与预期一致 | 通过 |
| `TC-MEM-001` | 记忆向量检索 | 已有记忆 | embedding | POST memory search | 返回相似结果 | 与预期一致 | 通过 |
| `TC-EXP-001` | TXT 导出 | 已有项目内容 | `format=txt` | GET export | 返回文本下载 | 与预期一致 | 通过 |
| `TC-EXP-002` | DOCX 导出 | 已有项目内容 | `format=docx` | GET export | 返回 DOCX 下载 | 与预期一致 | 通过 |
| `TC-AGT-001` | Agent 生成 run | 已有线程 | 用户消息 | 发消息生成 run | 返回待确认 run | 与预期一致 | 通过 |
| `TC-AGT-002` | Agent 确认执行 | 已有待确认 run | run_id | confirm / confirm-high-risk | 完成写入 | 与预期一致 | 通过 |
| `TC-EDT-001` | TipTap 内联改写 | 章节/场景编辑页 | 文本片段 | 触发 inline-edit SSE | 返回流式改写 | 路由测试通过 | 通过 |
| `TC-DND-001` | 前端拖拽排序 | 页面可访问 | 拖拽操作 | 章节/场景页面拖拽 | 顺序更新 | API + 页面链路通过 | 通过 |
| `TC-GPH-001` | 图谱页渲染 | 项目有关系数据 | 项目 ID | 打开 relationships 页面 | 页面构建通过 | 与预期一致 | 通过 |
| `TC-TML-001` | 时间线聚合 | 项目有 episode 记忆 | 项目 ID | GET timeline | 返回章节+事件 | 与预期一致 | 通过 |
| `TC-E2E-001` | 项目创建流程 | E2E server 正常 | 表单数据 | 浏览器创建项目 | 进入详情页 | 与预期一致 | 通过 |
| `TC-E2E-002` | Agent 创建人物 | fixture 模式 | 固定指令 | 浏览器走 Agent 流程 | 人物页可见 | 与预期一致 | 通过 |
| `TC-E2E-003` | 项目包导入导出 | fixture 模式 | 项目包文件 | 导出后导入 | 生成副本项目 | 与预期一致 | 通过 |

## 5. 失败与修复记录

### 首次 E2E 回归

- 结果：`7 failed`
- 现象：SQLite 表缺少 `story_outline` 列
- 根因：复用旧 `backend/e2e_test.db`
- 修复：启动前删除旧库
- 复测：`7 passed`

### 首次前端 type-check

- 结果：失败
- 现象：`.next/types` 缺失导致 `TS6053`
- 根因：脚本未先生成 route types
- 修复：改为 `next typegen && tsc --noEmit`
- 复测：通过

## 6. 覆盖率差距

覆盖率未达标的主要集中区：

- `app/services/agent_workflow.py`
- `app/agents/orchestrator.py`
- `app/api/v1/timeline.py`
- 若干 model / runtime 辅助分支

当前结论：

- 功能回归：通过
- 95% 覆盖率目标：未达成
