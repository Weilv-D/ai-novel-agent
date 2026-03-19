export default function ServerErrorPage() {
  return (
    <main className="ink-page">
      <div className="mx-auto max-w-lg px-4 py-20 text-center">
        <p className="ink-kicker mb-2">500</p>
        <h1 className="ink-display text-4xl font-semibold text-[rgb(var(--ink-950))]">
          服务暂时不可用
        </h1>
        <p className="mt-4 text-base leading-7 text-[rgb(var(--ink-800))]">
          发生了未预期的服务器错误，请稍后重试。
        </p>
      </div>
    </main>
  );
}
