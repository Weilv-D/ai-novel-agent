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
  "agent_profile_id": "string (default: 'default')",
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
  "age": "integer | null (>= 0)",
  "gender": "string | null",
  "role": "string | null",
  "personality": "string | null",
  "background": "string | null",
  "appearance": "string | null",
  "relationships": "object | null",
  "notes": "string | null",
  "meta": "object (default: {})"
}
```

**Response:** `201 Created`

### GET /characters/project/{project_id}

List all characters for a project.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| skip | integer | 0 | Number of records to skip |
| limit | integer | 100 | Maximum number of records |

### GET /characters/{character_id}

Get a character by ID.

### PATCH /characters/{character_id}

Update a character.

### DELETE /characters/{character_id}

Delete a character.

---

## World Settings

### POST /world-settings

Create a new world setting.

**Request Body:**

```json
{
  "project_id": "uuid (required)",
  "name": "string (required, 1-255 chars)",
  "category": "string | null",
  "content": "string (required)",
  "notes": "string | null",
  "meta": "object (default: {})"
}
```

**Response:** `201 Created`

### GET /world-settings/project/{project_id}

List all world settings for a project.

### GET /world-settings/project/{project_id}/category/{category}

List world settings by category.

### GET /world-settings/{setting_id}

Get a world setting by ID.

### PATCH /world-settings/{setting_id}

Update a world setting.

### DELETE /world-settings/{setting_id}

Delete a world setting.

---

## Volumes

### POST /volumes

Create a new volume.

**Request Body:**

```json
{
  "project_id": "uuid (required)",
  "name": "string (required, 1-255 chars)",
  "description": "string | null",
  "order": "integer (default: 0)"
}
```

**Response:** `201 Created`

### GET /volumes/project/{project_id}

List all volumes for a project.

### GET /volumes/{volume_id}

Get a volume by ID.

### PATCH /volumes/{volume_id}

Update a volume.

### DELETE /volumes/{volume_id}

Delete a volume.

---

## Chapters

### POST /chapters

Create a new chapter.

**Request Body:**

```json
{
  "project_id": "uuid (required)",
  "volume_id": "uuid | null",
  "title": "string (required, 1-255 chars)",
  "summary": "string | null",
  "content": "string | null",
  "order": "integer (default: 0)",
  "pov_character_id": "uuid | null"
}
```

**Response:** `201 Created`

### GET /chapters/project/{project_id}

List all chapters for a project.

### GET /chapters/volume/{volume_id}

List all chapters for a volume.

### GET /chapters/{chapter_id}

Get a chapter by ID.

### PATCH /chapters/{chapter_id}

Update a chapter.

### DELETE /chapters/{chapter_id}

Delete a chapter.

---

## Scenes

### POST /scenes

Create a new scene.

**Request Body:**

```json
{
  "chapter_id": "uuid (required)",
  "title": "string (required, 1-255 chars)",
  "summary": "string | null",
  "content": "string | null",
  "order": "integer (default: 0)",
  "pov_character_id": "uuid | null"
}
```

**Response:** `201 Created`

### GET /scenes/chapter/{chapter_id}

List all scenes for a chapter.

### GET /scenes/{scene_id}

Get a scene by ID.

### PATCH /scenes/{scene_id}

Update a scene.

### DELETE /scenes/{scene_id}

Delete a scene.

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
  "thread": { ... },
  "messages": [ ... ],
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
    "status": "awaiting_confirmation | awaiting_high_risk_confirmation | ...",
    "summary": "string | null",
    "operations": [ ... ],
    "risk_summary": {
      "overall_risk_level": "low | medium | high",
      "confirmation_gate": "none | single | double",
      "requires_confirmation": true,
      "requires_secondary_confirmation": false,
      ...
    },
    ...
  }
}
```

**Streaming Response:** SSE format

```
data: {"type": "status", "stage": "init", "message": "...", "timestamp": "..."}

data: {"type": "thinking", "stage": "planning", "message": "...", "detail": {...}}

data: {"type": "result", "stage": "complete", "message": "...", "detail": {...}}

data: [DONE]
```

### GET /agent/runs/{run_id}

Get a single run with operation previews/results.

### POST /agent/runs/{run_id}/confirm

Confirm and execute a planned run.

**Response:** `200 OK`

```json
{
  "run": {
    "status": "completed | failed",
    "operations": [ ... ],
    "verification_status": "passed | failed",
    ...
  }
}
```

### POST /agent/runs/{run_id}/confirm-high-risk

Execute a run after secondary confirmation for high-risk writes.

### POST /agent/runs/{run_id}/cancel

Cancel a run that has not been executed.

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
      "policy": { ... }
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
      "policy_id": "create_only | standard_updates | ...",
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
    "source": "string"
  },
  "operations": [
    {
      "name": "string",
      "description": "string",
      "kind": "operation",
      "tool_name": "string",
      "source": "string"
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

### POST /agent/chat/stream

Legacy streaming chat endpoint.

### POST /agent/auto-summarize

Legacy auto-summarize endpoint.

### POST /agent/continuity-check

Legacy continuity check endpoint.

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
