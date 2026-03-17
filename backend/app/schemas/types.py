"""Shared type definitions used across multiple schemas."""

from typing import Literal

TargetTypeLiteral = Literal[
    "project", "character", "world_setting", "volume", "chapter", "scene"
]

CONTENT_MAX_LENGTH = 500000
OUTLINE_MAX_LENGTH = 50000
NOTES_MAX_LENGTH = 10000
SUMMARY_MAX_LENGTH = 5000
MEMORY_CONTENT_MAX_LENGTH = 100000
