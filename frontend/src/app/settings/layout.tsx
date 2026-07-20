import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '设置',
  description: '管理你的账户信息和偏好。',
};

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
