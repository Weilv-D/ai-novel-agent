const HTML_TAG_PATTERN = /<\/?[a-z][\s\S]*>/i;
const ENTITY_MAP: Record<string, string> = {
  "&nbsp;": " ",
  "&amp;": "&",
  "&lt;": "<",
  "&gt;": ">",
  "&quot;": '"',
  "&#39;": "'",
};

function decodeEntities(text: string): string {
  return text.replace(/&nbsp;|&amp;|&lt;|&gt;|&quot;|&#39;/g, (entity) => ENTITY_MAP[entity] ?? entity);
}

export function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function isHtmlContent(content?: string | null): boolean {
  return typeof content === "string" && HTML_TAG_PATTERN.test(content);
}

export function normalizeRichTextContent(content?: string | null): string {
  if (!content) {
    return "";
  }

  if (isHtmlContent(content)) {
    return content;
  }

  const normalized = content.replace(/\r\n?/g, "\n").trim();
  if (!normalized) {
    return "";
  }

  return normalized
    .split(/\n{2,}/)
    .map((paragraph) => `<p>${escapeHtml(paragraph).replace(/\n/g, "<br />")}</p>`)
    .join("");
}

export function richTextToPlainText(content?: string | null): string {
  if (!content) {
    return "";
  }

  if (!isHtmlContent(content)) {
    return content.replace(/\r\n?/g, "\n").trim();
  }

  const withBreaks = content
    .replace(/\r\n?/g, "\n")
    .replace(/<li[^>]*>/gi, "\n- ")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(p|div|section|article|blockquote|pre|h1|h2|h3|h4|h5|h6|li|ul|ol)>/gi, "\n")
    .replace(/<[^>]+>/g, "");

  return decodeEntities(withBreaks)
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function hasRichTextContent(content?: string | null): boolean {
  return richTextToPlainText(content).trim().length > 0;
}

export function getRichTextPreview(content?: string | null, maxLength = 160): string {
  const plainText = richTextToPlainText(content);
  if (plainText.length <= maxLength) {
    return plainText;
  }
  return `${plainText.slice(0, maxLength).trimEnd()}...`;
}
