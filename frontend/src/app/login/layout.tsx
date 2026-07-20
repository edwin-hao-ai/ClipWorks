import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '登录',
  description: '登录 ClipWorks 映工厂，开始用 AI 生成视频。',
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  return children;
}
