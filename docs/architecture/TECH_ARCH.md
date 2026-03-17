# AI Novel Agent 目标架构

最后更新：2026-03-16

## 文档定位

本文档描述系统的目标架构与长期设计原则。它回答“系统应该如何被组织”，而不是“当前已经做到了哪里”。

如果你要查看：

- 当前真实实现：见 [TECH_IMPLEMENTATION.md](TECH_IMPLEMENTATION.md)
- 当前交付状态：见 [../qa/STATUS.md](../qa/STATUS.md)
- 后续演进顺序：见 [../roadmap/IMPLEMENTATION_PLAN.md](../roadmap/IMPLEMENTATION_PLAN.md)

## 架构目标

AI Novel Agent 的目标不是做一个泛化聊天壳，而是做一个围绕长篇小说创作的可验证 Agent 系统。目标架构满足以下要求：

- 以项目化数据结构承载长期创作
- 以 Agent Workspace 承载主要交互
- 让 AI 执行先计划、后确认、再写入
- 让执行过程可解释、可追踪、可验证
- 让长期线程在压缩后仍保留稳定的上下文边界

## 系统边界

系统当前和长期都以独立实例为基本运行单元：

- 不把多租户或组织权限作为核心前提
- 不依赖后台 worker 才能完成主工作流
- 不要求前端解析非结构化状态

访问控制保留为实例级 API key，业务核心不建立在用户系统之上。

## 总体拓扑

目标拓扑如下：

```text
Frontend Workspace
    |
    v
FastAPI API Layer
    |
    v
Workflow / Domain Services
    |              \
    |               \-> LLM / Embedding Providers
    v
PostgreSQL + pgvector
    |
    v
Redis (runtime dependency / health target)
```

## 分层原则

### 1. API 层

负责：

- 请求解析
- 实例级访问控制
- schema 校验
- 返回稳定 contract

API 层不承载业务编排。

### 2. Workflow 层

负责：

- 项目级 thread / run / operation 生命周期
- profile / skill 选择
- 风险分类与确认门槛
- execution contract 装配
- verification gate 触发
- compact flow 触发与上下文装配

### 3. Domain Service 层

负责：

- Project / Character / WorldSetting / Chapter / Scene CRUD
- Snapshot、Memory、Dependency、Export
- 领域内的数据一致性和复用逻辑

### 4. Contract 层

通过 schema 暴露稳定结构，而不是让调用方从 `meta` 推断：

- execution contract
- risk contract
- verification contract
- compact contract

### 5. Persistence 层

负责：

- 创作对象持久化
- Agent 运行数据持久化
- 向量存储与检索
- 快照与审计链

## Agent 架构原则

### 主流程

目标架构固定以项目级 `thread / run / operation` 作为公开工作流接口：

1. 用户向线程发送消息
2. 系统生成 run 和 operation 计划
3. 用户完成确认
4. 系统执行写入
5. 系统做 verification
6. 系统在需要时压缩线程上下文

### 内部角色

内部角色长期保持分层，而不退回单块 prompt：

- planner
- researcher
- writer
- editor
- continuity
- executor

这些角色应通过显式 child unit contract 协作。

### 风险与确认

风险分类必须独立于前端展示逻辑，目标分层为：

- capability policy
- risk policy registry
- applied policy snapshot
- run risk summary

### 校验

verification gate 是架构核心，而不是补充功能。目标校验层包括：

- 字段级一致性
- 快照一致性
- 内容迁移一致性
- 业务语义一致性

### 长线程

compact flow 不是简单摘要，而是受 contract 约束的上下文治理机制。目标包括：

- checkpoint
- planner window
- retained window
- active bundle contract
- 可解释的 compaction boundary

## 数据域划分

### 创作域

- Project
- Character
- WorldSetting
- Volume
- Chapter
- Scene

### 执行域

- AgentThread
- AgentMessage
- AgentRun
- AgentOperation
- AgentSubtask
- AgentThreadCheckpoint

### 审计与一致性域

- Snapshot
- Dependency
- Suggestion

### 检索域

- Memory

## Profile 与 Skill 体系

目标架构要求 skill 不再是全局字符串拼接，而是项目级策略系统：

- 项目绑定 profile
- profile 提供 planner / operation skill
- 运行期可查看实际加载的 profile 与 skill bundle
- 自定义扩展通过 profile 根目录覆盖实现

## 前端架构原则

前端长期保持以下结构：

- 项目详情页是主工作台
- 对象编辑页是辅助路径
- 前端直接消费稳定 contract
- 状态展示优先解释 execution / risk / verification / compact，而不是隐藏运行状态

## 部署与运维原则

当前优先支持：

- Docker Compose 本地部署
- PostgreSQL + pgvector
- Redis

更复杂的部署、协作和公网安全能力应建立在当前 contract 稳定之后，而不是在核心工作流未稳定时提前引入。
