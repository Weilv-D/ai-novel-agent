# 业务逻辑审查报告

审查日期：2026-03-17
审查执行者：AI Agent（单人环境）
审查方法：代码走查、路由与 schema 对照、主流程验证、异常路径复盘、全量 pytest、Playwright E2E、OpenAPI 对照

## 1. 审查范围

| 模块 | 验证重点 |
| --- | --- |
| Project / Volume / Chapter / Scene | 分层结构、默认卷、排序、详情与编辑一致性 |
| Character / WorldSetting | CRUD、唯一性规则、前端详情/编辑流 |
| Memory / Export / Timeline | 记忆写入、向量检索缓存、HTML 导出清洗、事件聚合 |
| Agent Workflow | thread / run / operation、确认门禁、流式输出 |
| Frontend Editor / DnD / Graph / Timeline | 编辑、排序、图谱、导航与页面链路 |
| E2E Infrastructure | 测试环境初始化、SQLite 基线、fixture 工作流 |

## 2. 逐项验证结果

| 验证项 | 结果 | 说明 |
| --- | --- | --- |
| 项目总纲 -> 卷 -> 章 -> 场景层级一致 | 通过 | 当前代码与页面已统一 |
| 项目创建/查询/删除逻辑 | 通过 | 后端测试和 E2E 均通过 |
| 默认卷与章节归属规则 | 通过 | 服务层有兼容处理 |
| 章节/场景重排持久化 | 通过 | 路由、服务和前端链路完整 |
| 人物与设定 CRUD | 通过 | API、页面和测试链路完整 |
| 富文本正文存储与导出清洗 | 通过 | 导出服务已清 HTML |
| 向量检索与缓存失效逻辑 | 通过 | memory service 测试覆盖 |
| Agent 计划、确认与执行主流程 | 通过 | 全量 pytest 与 E2E 覆盖主链路 |
| Graph / Timeline 页面装配 | 通过 | lint/build 通过，页面已接入 |
| Playwright E2E 环境稳定性 | 修复后通过 | 旧 SQLite 文件污染已修复 |
| 前端独立 type-check 稳定性 | 修复后通过 | 改为 `next typegen + tsc` |

## 3. 发现的问题

### E2E-001

- 标题：固定 SQLite E2E 数据库复用旧 schema，导致 `story_outline` 列缺失
- 位置：`playwright.config.ts` / `backend/e2e_test.db`
- 影响：7 个浏览器用例全部失败
- 根因：测试环境使用固定数据库文件，启动前未清理旧库
- 处理：新增 `backend/scripts/start_e2e_server.sh`，每次启动前删除旧 SQLite 文件
- 状态：已修复、已验证

### TOOL-001

- 标题：前端 `npm run type-check` 依赖过期 `.next/types`，单独执行不稳定
- 位置：`frontend/package.json`
- 影响：未先 build 时 `tsc` 报 `TS6053`
- 根因：脚本直接调用 `tsc --noEmit`，而 `tsconfig` 包含 `.next/types`
- 处理：脚本改为 `next typegen && tsc --noEmit`
- 状态：已修复、已验证

### QA-001

- 标题：后端 statement 覆盖率为 `90%`，未达到 `95%` 目标
- 位置：`backend/tests` 覆盖面整体
- 影响：流程性要求未满足
- 根因：`agent_workflow.py` 仍有大量复杂分支未覆盖
- 状态：未关闭

## 4. 方案评审说明

需求要求“至少两名团队成员参与修复方案评审”。当前仓库处于单人执行环境，本轮未能完成正式双人评审。

已采取替代措施：

- 全量测试 + E2E 回归
- 代码与文档双重自查
- 问题清单与根因显式记录

该流程缺口已在 [`ISSUE_TRACKER.md`](./ISSUE_TRACKER.md) 中保留跟踪。

## 5. 审查结论

当前核心业务逻辑未发现阻塞性缺陷。新增问题均属于测试基础设施和工具链稳定性问题，且已经修复并回归验证。系统剩余主要差距在流程合规和覆盖率目标，而非核心功能正确性。
