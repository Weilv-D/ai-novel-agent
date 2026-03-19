import type { Character } from "@/lib/types";

export interface CharacterRelation {
  targetId?: string;
  targetName?: string;
  label: string;
  note?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function looksLikeUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(value);
}

function normalizeCharacterName(value: string): string {
  return value.trim().toLocaleLowerCase("zh-CN");
}

function readFirstString(source: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = source[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return undefined;
}

function relationFromRecord(
  record: Record<string, unknown>,
  fallbackLabel: string,
  fallbackName?: string,
): CharacterRelation | null {
  const targetId = readFirstString(record, ["target_id", "character_id", "id"]);
  const targetName = readFirstString(record, ["target_name", "character_name", "name", "label"]) || fallbackName;
  const label = readFirstString(record, ["relation", "relationship", "type", "kind", "role"]) || fallbackLabel;
  const note = readFirstString(record, ["note", "description", "status"]);

  if (!targetId && !targetName) {
    return null;
  }

  return {
    targetId,
    targetName,
    label,
    note,
  };
}

function knownCharacterNameSet(characters: Character[]): Set<string> {
  return new Set(characters.map((character) => normalizeCharacterName(character.name)));
}

export function extractCharacterRelations(
  character: Character,
  allCharacters: Character[],
): CharacterRelation[] {
  const relationships = character.relationships;
  if (!relationships) {
    return [];
  }

  const knownCharacterNames = knownCharacterNameSet(allCharacters);
  const extracted: CharacterRelation[] = [];

  for (const [key, rawValue] of Object.entries(relationships)) {
    if (Array.isArray(rawValue)) {
      for (const item of rawValue) {
        if (typeof item === "string" && item.trim()) {
          extracted.push({ targetName: item.trim(), label: key });
        } else if (isRecord(item)) {
          const relation = relationFromRecord(item, key);
          if (relation) {
            extracted.push(relation);
          }
        }
      }
      continue;
    }

    if (typeof rawValue === "string" && rawValue.trim()) {
      const normalizedKey = normalizeCharacterName(key);
      const normalizedValue = normalizeCharacterName(rawValue);

      if (looksLikeUuid(key)) {
        extracted.push({ targetId: key, label: rawValue.trim() });
      } else if (knownCharacterNames.has(normalizedKey) || !knownCharacterNames.has(normalizedValue)) {
        extracted.push({ targetName: key.trim(), label: rawValue.trim() });
      } else {
        extracted.push({ targetName: rawValue.trim(), label: key.trim() });
      }
      continue;
    }

    if (!isRecord(rawValue)) {
      continue;
    }

    if (key === "entries" || key === "items" || key === "links") {
      for (const item of Object.values(rawValue)) {
        if (isRecord(item)) {
          const relation = relationFromRecord(item, "关系");
          if (relation) {
            extracted.push(relation);
          }
        }
      }
      continue;
    }

    const directRelation = relationFromRecord(rawValue, key);
    if (directRelation) {
      extracted.push(directRelation);
      continue;
    }

    for (const [nestedKey, nestedValue] of Object.entries(rawValue)) {
      if (typeof nestedValue === "string" && nestedValue.trim()) {
        extracted.push({
          targetId: looksLikeUuid(nestedKey) ? nestedKey : undefined,
          targetName: looksLikeUuid(nestedKey) ? undefined : nestedKey,
          label: key,
          note: nestedValue.trim(),
        });
      } else if (isRecord(nestedValue)) {
        const relation = relationFromRecord(
          nestedValue,
          key,
          looksLikeUuid(nestedKey) ? undefined : nestedKey,
        );
        if (relation) {
          extracted.push(relation);
        }
      }
    }
  }

  return extracted;
}
