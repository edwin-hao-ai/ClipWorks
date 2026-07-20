// 从自然语言一句话里解析项目意图（URL/画幅/时长/标题）。
// 首页输入框与新建项目对话框共用，保证两条入口行为一致。

export const QUICK_PROMPTS = [
  '小红书口播精剪',
  'SaaS 产品发布',
  '教程视频',
  '短视频广告',
  '生日祝福视频',
];

export function extractUrl(text: string): string | undefined {
  const match = text.match(/https?:\/\/[^\s]+/i);
  return match ? match[0] : undefined;
}

export function extractFormat(text: string): '16:9' | '9:16' | '1:1' | undefined {
  if (/9:16|竖屏|抖音|小红书/.test(text)) return '9:16';
  if (/1:1|方形/.test(text)) return '1:1';
  if (/16:9|横屏|YouTube|B站/.test(text)) return '16:9';
  return undefined;
}

export function extractDuration(text: string): number | undefined {
  const match = text.match(/(\d+)\s*秒/);
  return match ? parseInt(match[1], 10) : undefined;
}

export function makeProjectTitle(text: string): string {
  // Remove URLs and collapse whitespace so the title is readable.
  const withoutUrl = text.replace(/https?:\/\/[^\s]+/gi, '').trim();
  const clean = withoutUrl.replace(/\s+/g, ' ').trim() || '未命名项目';
  return clean.slice(0, 80);
}
