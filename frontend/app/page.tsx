import { PersonalSetupPanel } from "@/components/PersonalSetupPanel";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

const featureCards = [
  {
    title: "角色与世界观",
    description: "把人物、设定、章节放在同一创作坐标里，减少上下文切换。",
  },
  {
    title: "AI 修订建议",
    description: "建议生成、确认、应用链路完整，避免粗暴覆盖正文。",
  },
  {
    title: "个人工作流",
    description: "面向单人长期写作，重点是稳定和持续推进，不是多人协作外壳。",
  },
];

export default function HomePage() {
  return (
    <main className="ink-page">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-24">
        <div className="grid items-start gap-12 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="animate-wash-rise space-y-8">
            <span className="ink-kicker">Ink-Wash Writing Studio</span>
            <div className="space-y-5">
              <h1 className="ink-display max-w-4xl text-5xl font-semibold leading-[0.95] text-[rgb(var(--ink-950))] sm:text-6xl lg:text-7xl">
                把长篇小说创作
                <span className="block text-[rgb(var(--accent))]">变成有节奏的协作流程</span>
              </h1>
              <p className="max-w-2xl text-lg leading-8 text-[rgb(var(--ink-700))]">
                用更克制、更清晰的界面组织项目、角色、设定与章节。AI 不是喧宾夺主的按钮集合，
                而是嵌进创作流程里的辅助笔。
              </p>
              <p className="ink-note">
                对象级 AI 协作 · 修改传播 · 一致性维护 · 单用户本地写作工作台
              </p>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row">
              <Button size="lg" href="/projects">
                进入项目台
              </Button>
              <Button size="lg" variant="outline" href="/projects/new">
                新建小说项目
              </Button>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {featureCards.map((feature, index) => (
                <Card
                  key={feature.title}
                  className={`ink-grid-card animate-wash-rise ${index === 1 ? "stagger-1" : index === 2 ? "stagger-2" : ""}`}
                >
                  <CardHeader className="mb-3">
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="leading-7">{feature.description}</CardDescription>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section className="animate-wash-rise stagger-1 space-y-6">
            <Card className="animate-paper-float overflow-hidden rounded-[2rem] p-0">
              <div className="border-b border-[rgba(var(--line),0.12)] px-7 py-6">
                <p className="ink-kicker">Workspace Preview</p>
                <h2 className="ink-display mt-3 text-3xl font-semibold text-[rgb(var(--ink-950))]">
                  一张纸面，承载完整创作上下文
                </h2>
              </div>
              <div className="grid gap-6 px-7 py-7">
                <div className="rounded-[1.4rem] border border-[rgba(var(--line),0.12)] bg-[rgba(255,255,255,0.52)] p-5">
                  <div className="flex items-center justify-between">
                    <span className="ink-badge ink-badge-rust">写作中</span>
                    <span className="text-sm text-[rgb(var(--ink-600))]">Project / 山海夜航</span>
                  </div>
                  <p className="mt-4 text-base leading-7 text-[rgb(var(--ink-700))]">
                    以“项目 → 章节 → 场景”和“项目 → 人物 / 世界观”双线组织内容，减少信息散落。
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-[1.25rem] bg-[rgba(var(--ink-950),0.06)] p-4">
                    <div className="text-sm font-semibold tracking-[0.08em] text-[rgb(var(--ink-700))]">智能建议</div>
                    <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                      对连续性修复、设定冲突、场景改写提供可确认建议，而不是直接覆盖正文。
                    </p>
                  </div>
                  <div className="rounded-[1.25rem] bg-[rgba(var(--accent),0.08)] p-4">
                    <div className="text-sm font-semibold tracking-[0.08em] text-[rgb(var(--accent))]">个人模式</div>
                    <p className="mt-3 text-sm leading-7 text-[rgb(var(--ink-800))]">
                      后端已按单用户使用方式收口，本地使用时流程更直接。
                    </p>
                  </div>
                </div>
              </div>
            </Card>

            <PersonalSetupPanel />
          </section>
        </div>

        <div className="mt-14 text-center text-sm text-[rgb(var(--ink-600))]">
          <span>后端 API 文档：</span>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[rgb(var(--accent))] underline-offset-4 hover:underline"
          >
            /docs
          </a>
          <span>（开发环境）</span>
        </div>
      </div>
    </main>
  );
}
