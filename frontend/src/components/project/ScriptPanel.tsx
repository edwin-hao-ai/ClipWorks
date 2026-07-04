interface Props {
  sourceUrl?: string;
}

export function ScriptPanel({ sourceUrl }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="font-semibold text-slate-900 mb-4">脚本大纲</h3>
      <div className="space-y-3 text-sm text-slate-600">
        <div className="p-3 bg-slate-50 rounded-lg">
          <span className="font-medium text-slate-900">钩子：</span>
          还在手动做产品视频？试试 ClipWorks，一键生成。
        </div>
        <div className="p-3 bg-slate-50 rounded-lg">
          <span className="font-medium text-slate-900">场景 1：</span>
          展示产品首页截图，突出核心卖点。
        </div>
        <div className="p-3 bg-slate-50 rounded-lg">
          <span className="font-medium text-slate-900">场景 2：</span>
          用户痛点 + 解决方案动画。
        </div>
        <div className="p-3 bg-slate-50 rounded-lg">
          <span className="font-medium text-slate-900">结尾：</span>
          行动号召，访问 {sourceUrl || '官网'}。
        </div>
      </div>
    </div>
  );
}
