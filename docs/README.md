# Documentation Index

最后更新：2026-03-17

本目录已经按“产品、架构、开发、用户、API、质量保障、归档”重新整理。阅读顺序建议如下：

1. 产品背景与范围：[`product/PRD.md`](./product/PRD.md)
2. 当前技术实现：[`architecture/TECH_IMPLEMENTATION.md`](./architecture/TECH_IMPLEMENTATION.md)
3. 开发与部署：[`development/DEVELOPMENT.md`](./development/DEVELOPMENT.md)
4. 用户操作手册：[`user/USER_GUIDE.md`](./user/USER_GUIDE.md)
5. API 参考：[`api/API_REFERENCE.md`](./api/API_REFERENCE.md)
6. 质量状态：[`qa/STATUS.md`](./qa/STATUS.md)
7. 逻辑审查：[`qa/REVIEW_REPORT.md`](./qa/REVIEW_REPORT.md)
8. 测试报告：[`qa/TEST_REPORT.md`](./qa/TEST_REPORT.md)
9. 问题清单：[`qa/ISSUE_TRACKER.md`](./qa/ISSUE_TRACKER.md)

## 分类说明

### `product/`

- `PRD.md`：产品目标、用户价值、需求边界。

### `architecture/`

- `TECH_ARCH.md`：目标架构与长期设计原则。
- `TECH_IMPLEMENTATION.md`：当前代码基线、真实能力面、技术选型和落地状态。

### `roadmap/`

- `IMPLEMENTATION_PLAN.md`：后续演进方向和约束，不作为当前实现事实来源。

### `development/`

- `DEVELOPMENT.md`：环境要求、安装步骤、运行命令、验证方法。

### `user/`

- `USER_GUIDE.md`：面向使用者的工作流说明、常见操作与排错指南。

### `api/`

- `API_REFERENCE.md`：按资源分组的接口说明，基于当前代码的 OpenAPI 路径整理。

### `qa/`

- `STATUS.md`：当前交付状态和质量门结果。
- `REVIEW_REPORT.md`：系统性逻辑审查、验证项和问题分析。
- `TEST_REPORT.md`：测试环境、用例矩阵、执行结果和覆盖率结论。
- `ISSUE_TRACKER.md`：标准化问题跟踪清单。

### `archive/`

- `MVP_SCOPE.md`：历史阶段文档，仅保留为范围演进参考，不代表当前实现基线。

## 维护规则

- “当前实现”只以 `architecture/TECH_IMPLEMENTATION.md`、`api/API_REFERENCE.md`、`qa/*.md` 为准。
- 历史阶段文档不得与当前实现文档混写。
- 新增功能时，至少同步更新实现说明、API 文档和测试/问题清单。
- 运行结果、覆盖率和测试数字必须标注执行日期，避免长期悬挂旧数据。
