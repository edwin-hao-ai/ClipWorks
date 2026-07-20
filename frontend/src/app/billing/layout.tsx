import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '用量与套餐',
  description: '查看你的生成用量和套餐信息。',
};

export default function BillingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
