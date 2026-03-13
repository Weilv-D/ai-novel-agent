export default function HomePage() {
  return (
    <main className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-4">AI Novel Agent</h1>
        <p className="text-gray-600 mb-8">
          AI-powered long-form novel writing system
        </p>
        <div className="bg-blue-50 border border-blue-200 rounded p-4 mb-4">
          <p className="text-sm text-blue-800">
            <strong>Phase 2 前端骨架已初始化</strong>
          </p>
          <ul className="list-disc list-inside text-sm text-blue-700 mt-2 space-y-1">
            <li>Next.js 15 + TypeScript</li>
            <li>App Router 结构</li>
            <li>ESLint 配置</li>
          </ul>
        </div>
        <p className="text-sm text-gray-500">
          后端 API 文档:{" "}
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            /docs
          </a>
          {" "}(开发环境)
        </p>
      </div>
    </main>
  );
}
