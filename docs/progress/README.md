# AI Novel Agent - 进度追踪

## 已完成模块

### Core 基础设施
- [x] Base Models (UUIDMixin, TimestampMixin, Base)
- [x] Base Service (CRUD 抽象层)
- [x] API Dependencies (DB session, project validation)

### 项目核心实体
| 模块 | Models | Schemas | API | Service | Tests |
|------|--------|---------|-----|---------|-------|
| Project | ✅ | ✅ | ✅ | ✅ | ✅ |
| Character | ✅ | ✅ | ✅ | ✅ | ✅ |
| WorldSetting | ✅ | ✅ | ✅ | ✅ | ✅ |
| Volume | ✅ | ✅ | ✅ | ✅ | ✅ |
| Chapter | ✅ | ✅ | ✅ | ✅ | ✅ |
| Scene | ✅ | ✅ | ✅ | ✅ | ✅ |
| Suggestion | ✅ | ✅ | ✅ | ✅ | ✅ |

### 测试现状
- **总计**: 165 tests passed
- **覆盖**: API endpoints, Service layer, Schema validation

---

## 待实现模块

### 高优先级 (下一批)
| 模块 | Models | Schemas | API | Service | Tests |
|------|--------|---------|-----|---------|-------|
| Memory | ✅ | ❌ | ❌ | ❌ | ❌ |
| Snapshot | ✅ | ❌ | ❌ | ❌ | ❌ |
| Dependency | ✅ | ✅ | ❌ | ❌ | ❌ |

### 低优先级 (后续)
| 模块 | Models | Schemas | API | Service | Tests |
|------|--------|---------|-----|---------|-------|
| User | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 实现计划

### 已完成: Suggestion (三态修改系统)
- [x] SuggestionService (CRUD + 状态流转)
- [x] Suggestions API (/api/v1/suggestions)
- [x] 建议操作端点 (confirm, discard, commit)
- [x] API + Service 集成测试

### 后续批次
1. Memory (向量检索、叙事事实存储)
2. Snapshot (版本控制、回滚)
3. Dependency (影响分析、依赖追踪)
4. User (认证、权限)

---

## 技术栈

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Vector**: pgvector (for Memory embeddings)
- **Testing**: pytest + pytest-asyncio
- **Validation**: Pydantic v2

---

*最后更新: 2026-03-12*
