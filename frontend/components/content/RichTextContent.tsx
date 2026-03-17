import { normalizeRichTextContent } from "@/lib/rich-text";

interface RichTextContentProps {
  content?: string | null;
  className?: string;
}

export function RichTextContent({ content, className = "" }: RichTextContentProps) {
  const html = normalizeRichTextContent(content);

  if (!html) {
    return null;
  }

  return (
    <div
      className={`ink-richtext ${className}`.trim()}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
