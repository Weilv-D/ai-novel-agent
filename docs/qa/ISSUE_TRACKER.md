# 问题跟踪清单

最后更新：2026-03-17

| 问题ID | 标题 | 严重度 | 优先级 | 根因分类 | 责任人 | 预计解决时间 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `E2E-001` | 固定 SQLite E2E 数据库复用旧 schema 导致 7 个用例失败 | 高 | P1 | 环境/配置问题 | AI Agent | 2026-03-17 | 已验证 |
| `TOOL-001` | 前端 `type-check` 依赖旧 `.next/types`，单独执行不稳定 | 中 | P2 | 工具链配置 | AI Agent | 2026-03-17 | 已验证 |
| `QA-001` | 后端 statement 覆盖率 `90%`，未达到 `95%` 目标 | 中 | P2 | 测试覆盖不足 | AI Agent | 待排期 | 新建 |
| `PROC-001` | 当前为单人环境，未执行至少两名成员的正式方案评审 | 低 | P3 | 流程约束 | AI Agent / 项目负责人 | 待安排 | 新建 |

## 问题详情

### E2E-001

- 复现步骤：
  1. 直接执行 `npm run e2e`
  2. Playwright 启动后端并创建测试项目
  3. 后端抛出 `sqlite3.OperationalError: table projects has no column named story_outline`
- 预期结果：E2E 使用当前 schema 正常执行
- 实际结果：7 个用例全部失败
- 证据：
  - Playwright 失败截图：`test-results/e2e-E2E-测试套件-项目创建与管理-创建项目并进入项目工作台-chromium/test-failed-1.png`
  - 错误上下文：`test-results/e2e-E2E-测试套件-项目创建与管理-创建项目并进入项目工作台-chromium/error-context.md`
- 修复结果：新增 `backend/scripts/start_e2e_server.sh` 清理旧库，复测 `7 passed`

### TOOL-001

- 复现步骤：
  1. 在未先执行 build 的情况下运行 `cd frontend && npm run type-check`
  2. `tsc` 报 `.next/types/... not found`
- 预期结果：独立运行 type-check 应稳定通过
- 实际结果：脚本依赖旧 build 产物
- 修复结果：脚本改为 `next typegen && tsc --noEmit`

### QA-001

- 问题：覆盖率目标未达成
- 当前值：statement `90%`
- 目标值：`95%+`
- 影响：流程性目标不满足，但不阻塞当前功能交付

### PROC-001

- 问题：未满足“至少两名团队成员参与方案评审”的流程要求
- 说明：当前仓库在单人环境内执行，无法伪造双人评审记录
- 建议：由项目负责人安排人工评审并补签记录
