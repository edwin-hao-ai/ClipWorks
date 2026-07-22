import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { GenerationPanel } from '@/components/project/GenerationPanel';
import { Project, RenderJob } from '@/lib/types';

const mockProject: Project = {
  id: 'project-1',
  title: '测试项目',
  source_type: 'url',
  status: 'generating',
  target_format: '16:9',
  target_duration: 30,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const makeJob = (overrides?: Partial<RenderJob>): RenderJob => ({
  id: 'job-1',
  status: 'running',
  progress: 0,
  logs: [],
  ...overrides,
});

describe('GenerationPanel no-steps mode', () => {
  it('hides the Pipeline step list when steps is empty', () => {
    render(
      <GenerationPanel
        project={mockProject}
        latestJob={makeJob()}
        steps={[]}
        currentStepIndex={-1}
        currentDescription="生成中…"
      />
    );

    expect(screen.queryByText('理解需求')).not.toBeInTheDocument();
    expect(screen.queryByText('分析素材')).not.toBeInTheDocument();
  });

  it('shows the latest log message as status when steps is empty', () => {
    const job = makeJob({
      logs: [
        { time: '2024-01-01T00:00:01Z', message: '开始分析素材' },
        { time: '2024-01-01T00:00:02Z', message: '正在渲染第 3 个场景' },
      ],
    });

    render(
      <GenerationPanel
        project={mockProject}
        latestJob={job}
        steps={[]}
        currentStepIndex={-1}
        currentDescription="生成中…"
      />
    );

    // 状态文本与日志列表都会出现同一条消息。
    expect(screen.getAllByText('正在渲染第 3 个场景').length).toBeGreaterThanOrEqual(1);
  });

  it('uses job.progress when available, otherwise parses percentage from the latest log', () => {
    const { rerender } = render(
      <GenerationPanel
        project={mockProject}
        latestJob={makeJob({ progress: 42 })}
        steps={[]}
        currentStepIndex={-1}
        currentDescription="生成中…"
      />
    );

    expect(screen.getByText('总进度 42%')).toBeInTheDocument();

    rerender(
      <GenerationPanel
        project={mockProject}
        latestJob={makeJob({
          progress: 0,
          logs: [{ time: '2024-01-01T00:00:01Z', message: '渲染完成 67%' }],
        })}
        steps={[]}
        currentStepIndex={-1}
        currentDescription="生成中…"
      />
    );

    expect(screen.getByText('总进度 67%')).toBeInTheDocument();
  });

  it('keeps the log list visible in no-steps mode', () => {
    const job = makeJob({
      logs: [
        { time: '2024-01-01T00:00:01Z', message: '开始分析素材' },
        { time: '2024-01-01T00:00:02Z', message: '正在渲染第 3 个场景' },
      ],
    });

    render(
      <GenerationPanel
        project={mockProject}
        latestJob={job}
        steps={[]}
        currentStepIndex={-1}
        currentDescription="生成中…"
      />
    );

    expect(screen.getByText('开始分析素材')).toBeInTheDocument();
    expect(screen.getByText('Agent 执行日志')).toBeInTheDocument();
  });

  it('keeps placeholder warning unchanged in no-steps mode', () => {
    const job = makeJob({
      status: 'completed',
      output_url: '/api/static/sample.mp4',
      logs: [{ time: '2024-01-01T00:00:01Z', message: '⚠️ 真实渲染不可用' }],
    });

    render(
      <GenerationPanel
        project={mockProject}
        latestJob={job}
        steps={[]}
        currentStepIndex={-1}
        currentDescription="生成中…"
      />
    );

    expect(screen.getByText(/输出为占位视频/)).toBeInTheDocument();
  });
});
