import Link from 'next/link';
import { Film, ArrowLeft } from 'lucide-react';

// 法律页面（隐私政策/服务条款）共用骨架：无侧边栏的居中阅读版式，
// 未登录也可访问（登录页会链接到这里）。
export function LegalLayout({
  title,
  updatedAt,
  children,
}: {
  title: string;
  updatedAt: string;
  children: React.ReactNode;
}) {
  return (
    <main id="cw-main" className="min-h-dvh bg-background-base">
      <div className="mx-auto max-w-2xl px-6 py-10">
        <header className="flex items-center justify-between mb-10">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-content-primary hover:text-brand-400 transition-colors"
          >
            <span className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <Film className="w-4 h-4 text-content-inverse" />
            </span>
            <span className="font-semibold">ClipWorks 映工厂</span>
          </Link>
          <Link
            href="/"
            className="focus-ring inline-flex items-center gap-1.5 text-sm text-content-tertiary hover:text-content-primary transition-colors rounded-md px-2 py-1"
          >
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </Link>
        </header>

        <h1 className="text-2xl font-bold text-content-primary mb-2">{title}</h1>
        <p className="text-sm text-content-tertiary mb-6">最近更新：{updatedAt}</p>

        {/* 草案声明：演示版本文案未经法务审订，必须对用户明示 */}
        <div className="mb-10 text-sm text-warning bg-warning/10 border border-warning/25 rounded-md px-4 py-3 leading-relaxed">
          本文档为 <strong>草案 v0.1</strong>，仅用于演示环境，内容尚未经法务审订。
          产品正式发布时将替换为正式版本，届时我们会通过站内通知告知您。
        </div>

        <article className="space-y-9">{children}</article>

        <footer className="mt-12 pt-6 border-t border-border-subtle text-xs text-content-tertiary">
          ClipWorks 映工厂 · AI 视频工厂
        </footer>
      </div>
    </main>
  );
}

// 统一段落排版，避免两个页面重复一长串 className。
export function LegalSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-base font-semibold text-content-primary mb-3">{title}</h2>
      <div className="text-sm leading-relaxed text-content-secondary space-y-2 [&>ul]:list-disc [&>ul]:pl-5 [&>ul]:space-y-1.5">
        {children}
      </div>
    </section>
  );
}
