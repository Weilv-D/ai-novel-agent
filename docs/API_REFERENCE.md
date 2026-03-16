# API Reference

Last Updated: 2026-03-16

## Overview

AI Novel Agent provides a RESTful API for managing novel creation projects, characters, world settings, chapters, scenes, and Agent workflow operations. All endpoints are prefixed with `/api/v1`.

## Authentication

When `ADMIN_API_KEY` is configured in the backend environment, all business endpoints require authentication via a custom header:

```
X-API-Key: your-admin-api-key
```

The header name can be customized via `API_KEY_HEADER` environment variable.

## Base URL

```
http://localhost:8000/api/v1
```

## Response Format

All responses are in JSON format. Error responses follow this structure:

```json
{
  "detail": "Error message"
}
```

---

## Health Check

### GET /health

Check system health status.

**Response:**

```json
{
  "status": "healthy",
  "mode": "standalone",
  "database": "healthy",
  "redis": "healthy"
}
```

---

## Projects

### POST /projects

Create a new project.

**Request Body:**

```json
{
  "name": "string (required, 1-255 chars)",
  "genre": "string | null (max 100 chars)",
  "target_audience": "string | null (max 100 chars)",
  "target_word_count": "integer | null (>= 0)",
  "status": "drafting | writing | revising | completed (default: drafting)",
  "summary": "string | null",
  "notes": "string | null",
  "agent_profile_id": "string (default: 'default', 1-80 chars)",
  "meta": "object (default: {})"
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "name": "string",
  "genre": "string | null",
  "target_audience": "string | null",
  "target_word_count": "integer | null",
  "status": "string",
  "summary": "string | null",
  "notes": "string | null",
  "agent_profile_id": "string",
  "meta": "object",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /projects

List all projects.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "name": "string",
    ...
  }
]
```

### GET /projects/{project_id}

Get a project by ID.

**Response:** `200 OK`

### PATCH /projects/{project_id}

Update a project.

**Request Body:** Partial project fields

**Response:** `200 OK`

### DELETE /projects/{project_id}

Delete a project.

**Response:** `200 OK`

---

## Characters

### POST /characters

Create a new character.

**Request Body:**

```json
{
  "project_id": "uuid (required)",
  "name": "string (required, 1-255 chars)",
  "role": "string | null (max 100 chars)",
  "profile": "object (default: {})",
  "relationships": "object (default: {})",
  "arc_state": "object (default: {})",
  "notes": "string | null"
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| name | string | Character name (required) |
| role | string | Character role (protagonist, antagonist, etc.) |
| profile | object | Character profile data (appearance, personality, background, etc.) |
| relationships | object | Relationship network with other characters |
| arc_state | object | Character arc progression state |
| notes | string | Additional notes |

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "name": "string",
  "role": "string | null",
  "profile": "object",
  "relationships": "object",
  "arc_state": "object",
  "notes": "string | null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /characters/project/{project_id}

List all characters for a project.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

### GET /characters/{character_id}

Get a character by ID.

**Response:** `200 OK`

### PATCH /characters/{character_id}

Update a character.

**Request Body:**

```json
{
  "name": "string | null (1-255 chars)",
  "role": "string | null (max 100 chars)",
  "profile": "object | null",
  "relationships": "object | null",
  "arc_state": "object | null",
  "notes": "string | null"
}
```

**Response:** `200 OK`

### DELETE /characters/{character_id}

Delete a character.

**Response:** `200 OK`

---

## World Settings

### POST /world-settings

Create a new world setting.

**Request Body:**

```json
{
  "project_id": "uuid (required)",
  "category": "string (required, see categories below)",
  "name": "string (required, 1-255 chars)",
  "content": "string | null",
  "meta": "object (default: {})"
}
```

**Category Values:**

| Category | Description |
|----------|-------------|
| magic_system | Magic or power system |
| geography | World geography |
| history | World history |
| organization | Organizations and factions |
| technology | Technology level |
| culture | Cultural elements |
| religion | Religious systems |
| economy | Economic systems |
| rules | World rules and laws |
| other | Other settings |

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "category": "string",
  "name": "string",
  "content": "string | null",
  "meta": "object",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /world-settings/project/{project_id}

List all world settings for a project.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

### GET /world-settings/project/{project_id}/category/{category}

List world settings by category.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

### GET /world-settings/{setting_id}

Get a world setting by ID.

**Response:** `200 OK`

### PATCH /world-settings/{setting_id}

Update a world setting.

**Request Body:**

```json
{
  "category": "string | null",
  "name": "string | null (1-255 chars)",
  "content": "string | null",
  "meta": "object | null"
}
```

**Response:** `200 OK`

### DELETE /world-settings/{setting_id}

Delete a world setting.

**Response:** `200 OK`

---

## Volumes

### POST /volumes

Create a new volume.

**Request Body:**

```json
{
  "project_id": "uuid (required)",
  "volume_number": "integer | null (>= 1)",
  "title": "string | null (max 255 chars)",
  "outline": "string | null",
  "notes": "string | null"
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "volume_number": "integer | null",
  "title": "string | null",
  "outline": "string | null",
  "notes": "string | null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /volumes/project/{project_id}

List all volumes for a project.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

### GET /volumes/{volume_id}

Get a volume by ID.

**Response:** `200 OK`

### PATCH /volumes/{volume_id}

Update a volume.

**Request Body:**

```json
{
  "volume_number": "integer | null (>= 1)",
  "title": "string | null (max 255 chars)",
  "outline": "string | null",
  "notes": "string | null"
}
```

**Response:** `200 OK`

### DELETE /volumes/{volume_id}

Delete a volume.

**Response:** `200 OK`

---

## Chapters

### POST /chapters

Create a new chapter.

**Request Body:**

```json
{
  "project_id": "uuid (required)",
  "volume_id": "uuid | null",
  "chapter_number": "integer (required, >= 1)",
  "title": "string | null (max 255 chars)",
  "outline": "string | null",
  "content": "string | null",
  "status": "draft | writing | completed (default: draft)",
  "notes": "string | null"
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "volume_id": "uuid | null",
  "chapter_number": "integer",
  "title": "string | null",
  "outline": "string | null",
  "content": "string | null",
  "status": "string",
  "notes": "string | null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /chapters/project/{project_id}

List all chapters for a project.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

### GET /chapters/volume/{volume_id}

List all chapters for a volume.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

### GET /chapters/{chapter_id}

Get a chapter by ID.

**Response:** `200 OK`

### PATCH /chapters/{chapter_id}

Update a chapter.

**Request Body:**

```json
{
  "chapter_number": "integer | null (>= 1)",
  "title": "string | null (max 255 chars)",
  "outline": "string | null",
  "content": "string | null",
  "status": "draft | writing | completed | null",
  "notes": "string | null",
  "volume_id": "uuid | null"
}
```

**Response:** `200 OK`

### DELETE /chapters/{chapter_id}

Delete a chapter.

**Response:** `200 OK`

---

## Scenes

### POST /scenes

Create a new scene.

**Request Body:**

```json
{
  "chapter_id": "uuid (required)",
  "scene_order": "integer (required, >= 1)",
  "pov_character_id": "uuid | null",
  "location": "string | null (max 255 chars)",
  "content": "string | null",
  "meta": "object (default: {})"
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "chapter_id": "uuid",
  "scene_order": "integer",
  "pov_character_id": "uuid | null",
  "location": "string | null",
  "content": "string | null",
  "meta": "object",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /scenes/chapter/{chapter_id}

List all scenes for a chapter.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

### GET /scenes/{scene_id}

Get a scene by ID.

**Response:** `200 OK`

### PATCH /scenes/{scene_id}

Update a scene.

**Request Body:**

```json
{
  "scene_order": "integer | null (>= 1)",
  "pov_character_id": "uuid | null",
  "location": "string | null (max 255 chars)",
  "content": "string | null",
  "meta": "object | null"
}
```

**Response:** `200 OK`

### DELETE /scenes/{scene_id}

Delete a scene.

**Response:** `200 OK`

---

## Memories

Memories store narrative facts with vector embeddings for semantic search.

### POST /memories

Create a new memory with optional embedding.

**Request Body:**

```json
{
  "project_id": "uuid (required)",
  "memory_type": "string (required)",
  "content": "string (required)",
  "meta": "object (default: {})",
  "embedding": "array of floats | null",
  "auto_embed": "boolean (default: false)"
}
```

**Memory Types:**

| Type | Description |
|------|-------------|
| episode | Event summaries |
| semantic | World rules, character traits |
| fact | Specific facts that may be referenced |

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| memory_type | string | Type of memory |
| content | string | Memory content text |
| embedding | array | Vector embedding (dimension matches EMBEDDING_DIMENSION config) |
| auto_embed | boolean | Automatically generate embedding from content |

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "memory_type": "string",
  "content": "string",
  "meta": "object",
  "embedding": "array | null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /memories

List all memories for a project.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| project_id | uuid | required | Project ID |
| memory_type | string | null | Filter by memory type |
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

### GET /memories/type/{memory_type}

List memories of a specific type for a project.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| project_id | uuid | required | Project ID |
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

**Response:** `200 OK`

### GET /memories/count

Count memories for a project.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| project_id | uuid | required | Project ID |
| memory_type | string | null | Filter by memory type |

**Response:** `200 OK`

```json
{
  "count": 10,
  "project_id": "uuid",
  "memory_type": "string | null"
}
```

### POST /memories/search

Search memories by vector embedding similarity.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| project_id | uuid | required | Project ID |

**Request Body:**

```json
{
  "query_embedding": "array of floats (required, dimension matches EMBEDDING_DIMENSION)",
  "limit": "integer (default: 10, range: 1-100)",
  "threshold": "float (default: 0.7, range: 0.0-1.0)",
  "memory_type": "string | null"
}
```

**Response:** `200 OK`

```json
{
  "matches": [
    {
      "id": "uuid",
      "memory_type": "string",
      "content": "string",
      "meta": "object",
      "similarity": 0.85
    }
  ],
  "total_count": 5,
  "search_summary": "Found 5 memories with similarity >= 0.7"
}
```

### GET /memories/{memory_id}

Get a memory by ID.

**Response:** `200 OK`

### PATCH /memories/{memory_id}

Update a memory.

**Request Body:**

```json
{
  "content": "string | null",
  "memory_type": "string | null",
  "meta": "object | null",
  "embedding": "array | null",
  "auto_embed": "boolean | null"
}
```

**Response:** `200 OK`

### DELETE /memories/{memory_id}

Delete a memory.

**Response:** `200 OK`

---

## Suggestions

### POST /suggestions

Create a new suggestion.

### GET /suggestions/project/{project_id}

List all suggestions for a project.

### GET /suggestions/{suggestion_id}

Get a suggestion by ID.

### PATCH /suggestions/{suggestion_id}

Update a suggestion.

### DELETE /suggestions/{suggestion_id}

Delete a suggestion.

---

## Dependencies

### POST /dependencies

Create a new dependency.

### GET /dependencies/project/{project_id}

List all dependencies for a project.

### GET /dependencies/{dependency_id}

Get a dependency by ID.

### PATCH /dependencies/{dependency_id}

Update a dependency.

### DELETE /dependencies/{dependency_id}

Delete a dependency.

---

## Snapshots

### POST /snapshots

Create a new snapshot.

### GET /snapshots/project/{project_id}

List all snapshots for a project.

### GET /snapshots/{snapshot_id}

Get a snapshot by ID.

### PATCH /snapshots/{snapshot_id}

Update a snapshot.

### DELETE /snapshots/{snapshot_id}

Delete a snapshot.

---

## Agent Workflow

### POST /agent/threads

Create or get the default thread for a project.

**Request Body:**

```json
{
  "project_id": "uuid"
}
```

**Response:** `200 OK`

```json
{
  "id": "uuid",
  "project_id": "uuid",
  "title": "string",
  "is_default": true,
  "meta": "object",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /agent/threads/{thread_id}

Get thread state with messages and recent runs.

**Response:** `200 OK`

```json
{
  "thread": {
    "id": "uuid",
    "project_id": "uuid",
    "title": "string",
    "is_default": true,
    "meta": "object",
    "created_at": "datetime",
    "updated_at": "datetime"
  },
  "messages": [
    {
      "id": "uuid",
      "thread_id": "uuid",
      "role": "user | assistant | system",
      "content": "string",
      "meta": "object",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "recent_runs": [ ... ],
  "current_run": { ... } | null,
  "latest_checkpoint": { ... } | null
}
```

### POST /agent/threads/{thread_id}/messages

Send a message to an agent thread and receive a planned run.

**Request Body:**

```json
{
  "content": "string (required, min 1 char)",
  "context": "object (default: {})",
  "stream": "boolean (default: false)"
}
```

**Non-streaming Response:** `200 OK`

```json
{
  "thread": { ... },
  "user_message": { ... },
  "assistant_message": { ... },
  "run": {
    "id": "uuid",
    "thread_id": "uuid",
    "project_id": "uuid",
    "user_message_id": "uuid | null",
    "assistant_message_id": "uuid | null",
    "revision_of_run_id": "uuid | null",
    "status": "awaiting_confirmation | awaiting_high_risk_confirmation | ...",
    "summary": "string | null",
    "error_message": "string | null",
    "warning_message": "string | null",
    "verification_status": "pending | passed | failed | skipped",
    "verification_summary": "string | null",
    "execution_contract": { ... },
    "risk_summary": {
      "policy_version": "string",
      "overall_risk_level": "low | medium | high",
      "confirmation_gate": "none | single | double",
      "requires_confirmation": true,
      "requires_secondary_confirmation": false,
      "total_operations": 1,
      "low_risk_operation_count": 1,
      "medium_risk_operation_count": 0,
      "high_risk_operation_count": 0,
      "high_risk_operation_positions": [],
      "secondary_confirmation_operation_positions": [],
      "applied_policies": [ ... ],
      "summary": "string"
    },
    "compact_policy": { ... },
    "planner_window": { ... },
    "retained_window": { ... },
    "active_bundle_contract": { ... },
    "meta": "object",
    "confirmed_at": "datetime | null",
    "secondary_confirmed_at": "datetime | null",
    "started_at": "datetime | null",
    "completed_at": "datetime | null",
    "created_at": "datetime",
    "updated_at": "datetime",
    "operations": [ ... ],
    "subtasks": [ ... ]
  }
}
```

**Streaming Response:** SSE format

```
data: {"type": "status", "stage": "init", "message": "...", "timestamp": "...", "detail": {}}

data: {"type": "thinking", "stage": "planning", "message": "...", "detail": {...}}

data: {"type": "operation_progress", "stage": "prepare", "message": "...", "detail": {...}}

data: {"type": "result", "stage": "complete", "message": "...", "detail": {...}}

data: [DONE]
```

**Stream Event Types:**

| Type | Stage | Description |
|------|-------|-------------|
| status | init, load_context, compact_check, prepare_operations, risk_assessment | Status updates |
| thinking | planning, plan_complete | Agent thinking process |
| operation_progress | prepare | Operation preparation progress |
| verification | - | Verification results |
| message_chunk | assistant_message | Assistant message chunks |
| result | complete | Final execution result |
| error | - | Error information |

### GET /agent/runs/{run_id}

Get a single run with operation previews/results.

**Response:** `200 OK`

### POST /agent/runs/{run_id}/confirm

Confirm and execute a planned run.

**Response:** `200 OK`

```json
{
  "run": {
    "status": "completed | failed",
    "verification_status": "passed | failed",
    "operations": [ ... ],
    ...
  }
}
```

### POST /agent/runs/{run_id}/confirm-high-risk

Execute a run after secondary confirmation for high-risk writes.

**Response:** `200 OK`

### POST /agent/runs/{run_id}/cancel

Cancel a run that has not been executed.

**Response:** `200 OK`

---

## Agent Configuration

### GET /agent/profiles

List available agent profiles.

**Response:** `200 OK`

```json
[
  {
    "id": "default",
    "name": "Default Profile",
    "description": "string",
    "builtin": true,
    "root": "/path/to/profile"
  }
]
```

### GET /agent/capabilities

Get the capability registry.

**Response:** `200 OK`

```json
{
  "registry_version": "string",
  "capabilities": [
    {
      "capability_id": "string",
      "name": "string",
      "kind": "read_search | planning | writing | editing | verification",
      "description": "string",
      "tool_scope": ["..."],
      "policy": {
        "execution_phase": "plan | build",
        "source_role": "planner | researcher | writer | editor | continuity | executor",
        "confirmation_gate": "none | single | double",
        "internal_only": true,
        "requires_confirmation": false
      },
      "execution_record": {
        "record_id": "string",
        "source_role": "string",
        "status": "planned | completed | failed | skipped",
        "tool_scope": ["..."],
        "input_summary": "string | null",
        "output_summary": "string | null",
        "attempt_count": 1
      }
    }
  ]
}
```

### GET /agent/risk-policies

Get the risk policy registry.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| project_id | uuid | Filter by project |
| profile_id | string | Filter by profile |

**Response:** `200 OK`

```json
{
  "policy_version": "string",
  "policies": [
    {
      "policy_id": "create_only | standard_updates | content_append | content_rewrite | long_form_overwrite | multi_object_write",
      "name": "string",
      "scope": "operation | run",
      "description": "string",
      "risk_level": "low | medium | high",
      "confirmation_gate": "none | single | double",
      "requires_secondary_confirmation": false,
      "tool_scope": ["..."]
    }
  ]
}
```

### GET /agent/skills

Get the active skill catalog.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| project_id | uuid | Get project-specific skills |

**Response:** `200 OK`

```json
{
  "profile_id": "string",
  "profile_name": "string",
  "builtin": true,
  "source_roots": ["..."],
  "planner": {
    "name": "string",
    "description": "string",
    "kind": "planner",
    "source": "string",
    "payload_contract": "string | null",
    "references": ["..."]
  },
  "operations": [
    {
      "name": "string",
      "description": "string",
      "kind": "operation",
      "tool_name": "string | null",
      "source": "string",
      "payload_contract": "string | null",
      "references": ["..."]
    }
  ]
}
```

---

## Export

### GET /projects/{project_id}/export

Export project content.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| format | string | txt | Export format: `txt` or `markdown` |

**Response:** Plain text file download

---

## Project Package

### GET /projects/{project_id}/package

Export a project as a downloadable ZIP package.

**Response:** ZIP file download

The ZIP contains:
- `manifest.json`: Package metadata
- `project_bundle.json`: Complete project data

### POST /projects/import

Import a project from an uploaded ZIP package.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | file | yes | ZIP package file |
| new_name | string | no | New project name |

**Response:** `200 OK`

```json
{
  "project_id": "uuid",
  "project_name": "string",
  "imported_counts": {
    "characters": 5,
    "world_settings": 10,
    "volumes": 2,
    "chapters": 20,
    "scenes": 50,
    "dependencies": 30,
    "snapshots": 100,
    "memories": 15
  },
  "warnings": [
    {
      "code": "embedding_dimension_mismatch",
      "message": "string",
      "details": {}
    }
  ]
}
```

---

## Legacy Endpoints

These endpoints are maintained for backward compatibility.

### POST /agent/chat

Legacy chat endpoint.

**Request Body:**

```json
{
  "project_id": "string (required)",
  "message": "string (required, min 1 char)",
  "history": "array of objects (default: [])",
  "context": "object (default: {})"
}
```

**Response:** `200 OK`

```json
{
  "message": "string",
  "suggestions": [],
  "metadata": {}
}
```

### POST /agent/chat/stream

Legacy streaming chat endpoint.

**Response:** SSE format

### POST /agent/auto-summarize

Legacy auto-summarize endpoint.

**Request Body:**

```json
{
  "project_id": "string",
  "chapter_id": "string",
  "content": "string (required, min 1 char)"
}
```

**Response:** `200 OK`

```json
{
  "memories": [],
  "count": 0
}
```

### POST /agent/continuity-check

Legacy continuity check endpoint.

**Request Body:**

```json
{
  "project_id": "string",
  "content": "string (required, min 1 char)"
}
```

**Response:** `200 OK`

```json
{
  "message": "string",
  "suggestions": [],
  "metadata": {}
}
```

---

## Error Codes

| HTTP Status | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Missing or invalid API key |
| 403 | Forbidden - Valid API key but insufficient permissions |
| 404 | Not Found - Resource does not exist |
| 422 | Unprocessable Entity - Validation error |
| 500 | Internal Server Error |

---

## Run Status Values

| Status | Description |
|--------|-------------|
| draft | Initial state |
| awaiting_confirmation | Plan ready, waiting for user confirmation |
| awaiting_high_risk_confirmation | High-risk operation, needs secondary confirmation |
| executing | Currently executing |
| completed | Successfully completed |
| failed | Execution failed |
| cancelled | Cancelled by user |
| superseded | Replaced by a newer run |

---

## Operation Status Values

| Status | Description |
|--------|-------------|
| planned | Planned but not executed |
| executed | Successfully executed |
| failed | Execution failed |
| cancelled | Cancelled |

---

## Risk Levels

| Level | Description |
|-------|-------------|
| low | Low risk, no confirmation required |
| medium | Medium risk, single confirmation required |
| high | High risk, secondary confirmation required |

---

## Verification Status

| Status | Description |
|--------|-------------|
| pending | Verification not yet performed |
| passed | All verifications passed |
| failed | One or more verifications failed |
| skipped | Verification skipped |

---

## Domain Verification Rules

### Character

| Rule ID | Description |
|---------|-------------|
| character_name_empty | Name cannot be empty |
| character_name_duplicate | Name must be unique within project |
| character_age_invalid | Age must be non-negative integer |

### WorldSetting

| Rule ID | Description |
|---------|-------------|
| world_setting_name_empty | Name cannot be empty |
| world_setting_content_empty | Content cannot be empty |
| world_setting_name_duplicate | Name must be unique within category |

### Chapter/Scene

| Rule ID | Description |
|---------|-------------|
| chapter_number_unique | Chapter number must be unique within project |
| scene_order_unique | Scene order must be unique within chapter |
