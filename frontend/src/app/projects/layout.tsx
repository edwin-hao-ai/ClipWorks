import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '项目库',
  description: '管理和生成你的 AI 视频项目。',
};

export default function ProjectsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
