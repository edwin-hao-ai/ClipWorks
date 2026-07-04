import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ClipWorks 映工厂',
  description: 'AI 驱动的视频生成与剪辑工具',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
