// 早期的演示数据（DEMO_USER / DEMO_PROJECTS / DEMO_ASSETS 等）已随各页面
// 改为真实 API + 错误横幅而全部移除，此处仅保留仍被 ProjectCard 使用的工具函数。
export function formatDuration(seconds?: number): string {
  if (seconds === undefined) return '--:--';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
