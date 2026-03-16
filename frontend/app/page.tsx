import { PersonalSetupPanel } from "@/components/PersonalSetupPanel";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

const featureCards = [
  {
    title: "角色与世界观",
    description: "人物、设定、章节同处于一纸之上，挥毫泼墨不被打断。",
  },
  {
    title: "Agent 计划执行",
    description: "直接用自然语言下达目标，先看完整计划和预览，再确认落笔。",
  },
  {
    title: "匠心工作流",
    description: "专为长期写作者打磨印刻，重点在沉淀，而非喧闹。",
  },
];

export default function HomePage() {
  return (
    <main className="ink-page bg-paper-grain min-h-screen text-ink-950 font-serif overflow-hidden">
      <div className="mx-auto max-w-6xl px-6 py-16 sm:px-8 sm:py-24 relative z-10">
        <div className="grid items-start gap-16 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="animate-wash-rise space-y-10 relative">

            {/* The beautiful modern decorative element */}
            <div className="absolute -left-12 top-4 hidden md:block">
              <span className="ink-kicker-text text-seal-dark text-xl font-medium tracking-[0.4em] mix-blend-multiply">
                水墨行间 • 沉浸书写
              </span>
            </div>

            <span className="ink-kicker">Ink-Wash Studio</span>
            <div className="space-y-6">
              <h1 className="ink-display max-w-4xl text-5xl font-medium leading-tight text-ink-950 sm:text-6xl lg:text-7xl">
                把长篇创作<br/>
                <span className="block text-seal-dark italic drop-shadow-sm mt-3">融于宣纸间的呼吸</span>
              </h1>
              <p className="max-w-2xl text-lg leading-relaxed text-ink-800 tracking-wide font-light">
                用克制、精致的界面组织项目与章节。<br/>
                Agent 不是浮在表面的聊天玩具，而是藏在砚台下、能规划并执行创作动作的那支生花妙笔。
              </p>
              <div className="inline-flex items-center gap-4 rounded-md border border-line/50 bg-[var(--surface-subtle)] px-4 py-2">
                 <span className="w-2 h-2 rounded-full bg-jade animate-pulse"></span>
                 <p className="ink-note tracking-wider text-ink-800">单用户本地协作台 · 实时对象同步 · 语境连贯</p>
              </div>
            </div>

            <div className="flex flex-col gap-5 sm:flex-row pt-4">
              <Button size="lg" href="/projects" className="font-display text-lg tracking-widest px-10">
                启卷
              </Button>
              <Button size="lg" variant="outline" href="/projects/new" className="font-display text-lg tracking-widest px-10">
                新篇
              </Button>
            </div>

            <div className="grid gap-6 sm:grid-cols-3 pt-6 border-t border-line/30">
              {featureCards.map((feature, index) => (
                <Card
                  key={feature.title}
                  className={`ink-grid-card animate-wash-rise border border-line/50 bg-[var(--surface-elevated)] shadow-sm backdrop-blur-md ${index === 1 ? "stagger-1" : index === 2 ? "stagger-2" : ""}`}
                >
                  <CardHeader className="mb-2">
                    <CardTitle className="text-lg font-medium text-ink-900 border-l-2 border-seal pl-2">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="leading-relaxed text-ink-800 tracking-wide">{feature.description}</CardDescription>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>

          <section className="animate-wash-rise stagger-1 space-y-8 relative">
             <div className="absolute -inset-4 bg-gradient-to-br from-paper-soft/35 to-transparent -z-10 rounded-2xl blur-xl"></div>

            <Card className="animate-paper-float overflow-hidden rounded-2xl border border-line/50 bg-[var(--surface-subtle)] p-0 backdrop-blur-xl shadow-2xl shadow-ink-900/12">
              <div className="border-b border-line/40 bg-[rgba(var(--paper-soft),0.78)] px-8 py-5">
                <p className="ink-kicker !text-jade">Workspace</p>
                <h2 className="ink-display mt-2 text-2xl font-medium text-ink-900">
                  一纸清白，承载万象
                </h2>
              </div>
              <div className="grid gap-6 px-8 py-8 bg-gradient-to-b from-transparent to-paper-deep/30">
                <div className="rounded-xl border border-line/45 bg-[var(--surface-strong)] p-6 shadow-sm transition-shadow hover:shadow-md">
                  <div className="flex items-center justify-between border-b border-dashed border-line/50 pb-3 mb-3">
                    <span className="ink-badge ink-badge-rust">挥毫中</span>
                    <span className="text-sm text-ink-800 font-serif tracking-widest">山海夜航</span>
                  </div>
                  <p className="mt-2 text-md leading-relaxed text-ink-900">
                    以&ldquo;卷 → 章 → 节&rdquo;和&ldquo;谱系 → 风象&rdquo;双线织网，灵感不散落。
                  </p>
                </div>
                <div className="grid gap-5 sm:grid-cols-2">
                  <div className="rounded-xl border border-line/30 bg-[var(--surface-tint)] p-5 transition-transform hover:-translate-y-1">
                    <div className="text-sm font-medium tracking-widest text-ink-900 mb-2 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-jade rounded-full"></span>
                        Agent Workspace
                    </div>
                    <p className="text-sm leading-relaxed text-ink-800">
                      在项目里直接下达&ldquo;创建人物&rdquo;&ldquo;修改设定&rdquo;&ldquo;重写章节&rdquo;这类指令，先拿到可执行计划与预览。
                    </p>
                  </div>
                  <div className="rounded-xl border border-seal/30 bg-[var(--surface-seal-soft)] p-5 transition-transform hover:-translate-y-1">
                    <div className="text-sm font-medium tracking-widest text-seal-dark mb-2 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-seal rounded-full"></span>
                        沉浸模式
                    </div>
                    <p className="text-sm leading-relaxed text-ink-800">
                      专注的本地工作流，去掉浮华的协作用语，将笔与纸交还自己手中。
                    </p>
                  </div>
                </div>
              </div>
            </Card>

            <PersonalSetupPanel />
          </section>
        </div>

        <div className="mt-20 flex flex-col items-center gap-3 text-center">
          <div className="w-12 h-px bg-line/70"></div>
          <div className="text-sm text-ink-800 tracking-widest font-serif">
            <span>后端 API 卷轴：</span>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-seal-dark underline-offset-4 hover:text-seal transition-colors"
            >
              /docs
            </a>
          </div>
        </div>
      </div>
    </main>
  );
}
