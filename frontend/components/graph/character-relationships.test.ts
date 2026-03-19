import test from "node:test";
import assert from "node:assert/strict";

import type { Character } from "@/lib/types";

import { extractCharacterRelations } from "./character-relationships";

function buildCharacter(overrides: Partial<Character>): Character {
  return {
    id: overrides.id || "character-id",
    project_id: overrides.project_id || "project-id",
    name: overrides.name || "默认角色",
    role: overrides.role,
    profile: overrides.profile,
    relationships: overrides.relationships,
    arc_state: overrides.arc_state,
    notes: overrides.notes,
    created_at: overrides.created_at || new Date().toISOString(),
    updated_at: overrides.updated_at || new Date().toISOString(),
  };
}

test("extractCharacterRelations supports imported name-to-label mappings", () => {
  const characters = [
    buildCharacter({
      id: "linxiao-id",
      name: "林霄",
      relationships: { 苏晚: "同行者" },
    }),
    buildCharacter({
      id: "suwan-id",
      name: "苏晚",
      relationships: {},
    }),
  ];

  const relations = extractCharacterRelations(characters[0], characters);

  assert.deepEqual(relations, [{ targetName: "苏晚", label: "同行者" }]);
});

test("extractCharacterRelations keeps reverse legacy mappings when the value is the known character", () => {
  const characters = [
    buildCharacter({
      id: "linxiao-id",
      name: "林霄",
      relationships: { 同行者: "苏晚" },
    }),
    buildCharacter({
      id: "suwan-id",
      name: "苏晚",
      relationships: {},
    }),
  ];

  const relations = extractCharacterRelations(characters[0], characters);

  assert.deepEqual(relations, [{ targetName: "苏晚", label: "同行者" }]);
});

test("extractCharacterRelations keeps imported title-style targets as external characters", () => {
  const characters = [
    buildCharacter({
      id: "luchen-id",
      name: "陆沉",
      relationships: { 师父: "引路人" },
    }),
  ];

  const relations = extractCharacterRelations(characters[0], characters);

  assert.deepEqual(relations, [{ targetName: "师父", label: "引路人" }]);
});
