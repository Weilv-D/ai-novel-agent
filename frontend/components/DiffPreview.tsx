"use client";

interface DiffPreviewProps {
  before: string;
  after: string;
  title?: string;
}

export function DiffPreview({ before, after, title }: DiffPreviewProps) {
  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-[rgba(var(--line),0.12)]">
      {title && (
        <div className="border-b border-[rgba(var(--line),0.12)] bg-[rgba(var(--ink-950),0.04)] px-4 py-3 text-sm font-medium text-[rgb(var(--ink-700))]">
          {title}
        </div>
      )}
      <div className="grid grid-cols-1 divide-y divide-[rgba(var(--line),0.12)] md:grid-cols-2 md:divide-x md:divide-y-0">
        <div className="p-4">
          <div className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-[rgb(var(--danger))]">修改前</div>
          <div className="rounded-[1rem] bg-[rgba(var(--danger),0.07)] p-3 text-sm whitespace-pre-wrap text-[rgb(var(--ink-800))]">
            {before || "（空）"}
          </div>
        </div>
        <div className="p-4">
          <div className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-[rgb(var(--jade))]">修改后</div>
          <div className="rounded-[1rem] bg-[rgba(var(--jade),0.08)] p-3 text-sm whitespace-pre-wrap text-[rgb(var(--ink-800))]">
            {after || "（空）"}
          </div>
        </div>
      </div>
    </div>
  );
}
