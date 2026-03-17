import Link from "next/link";

export default function NotFound() {
  return (
    <main className="ink-page">
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="ink-kicker mb-2">404</p>
        <h1 className="ink-display text-4xl font-semibold text-[rgb(var(--ink-950))]">
          页面未找到
        </h1>
        <p className="mt-4 text-base leading-7 text-[rgb(var(--ink-800))]">
          你访问的页面不存在，可能已被移除或地址有误。
        </p>
        <div className="mt-8">
          <Link
            href="/projects"
            className="inline-flex items-center rounded-[1rem] border border-[rgba(var(--line),0.18)] bg-[rgba(var(--ink-950),0.94)] px-6 py-3 text-sm font-medium text-[rgb(var(--paper-soft))] transition-all hover:bg-[rgba(var(--ink-950),1)]"
          >
            返回项目列表
          </Link>
        </div>
      </div>
    </main>
  );
}
