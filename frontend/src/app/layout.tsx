import type { Metadata } from 'next';
import localFont from 'next/font/local';
import './globals.css';

// 本地托管可变字体（latin 子集），CJK 回落系统字体；避免构建时依赖 Google Fonts 网络。
const inter = localFont({
  src: './fonts/InterVariable.woff2',
  variable: '--font-sans',
  display: 'swap',
  fallback: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
});

const jetbrainsMono = localFont({
  src: './fonts/JetBrainsMonoVariable.woff2',
  variable: '--font-mono',
  display: 'swap',
  fallback: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
});

// 主题在 hydration 前从 localStorage 应用，避免浅色用户看到暗色闪屏（FOUC）。
const themeScript = `
(function () {
  try {
    if (window.localStorage.getItem('cw_theme') === 'light') {
      document.documentElement.dataset.theme = 'light';
    }
  } catch (e) {}
})();
`;

export const metadata: Metadata = {
  // 站点根 URL 走环境变量，未配置时回落本地开发地址（影响 OG 图片等绝对 URL 生成）。
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000'),
  title: {
    default: 'ClipWorks 映工厂',
    template: '%s - ClipWorks 映工厂',
  },
  description: 'AI 驱动的视频生成与剪辑工具：一句话，一段素材，一条成片。',
  applicationName: 'ClipWorks',
  openGraph: {
    type: 'website',
    siteName: 'ClipWorks 映工厂',
    title: 'ClipWorks 映工厂',
    description: 'AI 驱动的视频生成与剪辑工具：一句话，一段素材，一条成片。',
    locale: 'zh_CN',
  },
  twitter: {
    card: 'summary',
    title: 'ClipWorks 映工厂',
    description: 'AI 驱动的视频生成与剪辑工具：一句话，一段素材，一条成片。',
  },
  robots: { index: false, follow: false },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="zh-CN"
      className={`dark ${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body className="antialiased bg-background-base text-content-primary min-h-dvh font-sans">
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
        <a
          href="#cw-main"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2 focus:rounded-md focus:bg-brand-600 focus:text-content-inverse focus:text-sm focus:font-medium"
        >
          跳到主要内容
        </a>
        {children}
      </body>
    </html>
  );
}
