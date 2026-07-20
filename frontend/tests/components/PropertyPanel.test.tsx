import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PropertyPanel } from '@/components/project/PropertyPanel';
import { Project, Scene, MediaAsset } from '@/lib/types';

const scenes: Scene[] = [
  { id: 's1', index: 0, name: '开场', start_time: 0, duration: 5 },
  { id: 's2', index: 1, name: '正文', start_time: 5, duration: 10 },
];

const mockProject: Project = {
  id: 'p1',
  title: 'Test',
  source_type: 'url',
  status: 'draft',
  target_format: '16:9',
  target_duration: 30,
  created_at: '',
  updated_at: '',
};

const mockAssets: MediaAsset[] = [
  {
    id: 'a1',
    project_id: 'p1',
    type: 'image',
    source: 'upload',
    original_url: '/assets/shot.png',
    created_at: '',
  },
  {
    id: 'a2',
    project_id: 'p1',
    type: 'audio',
    source: 'upload',
    original_url: '/assets/bgm.mp3',
    created_at: '',
  },
];

describe('PropertyPanel', () => {
  it('renders project title', () => {
    render(<PropertyPanel project={mockProject} />);
    expect(screen.getByDisplayValue('Test')).toBeInTheDocument();
  });

  it('renders source_url input', () => {
    render(<PropertyPanel project={{ ...mockProject, source_url: 'https://example.com' }} />);
    expect(screen.getByDisplayValue('https://example.com')).toBeInTheDocument();
  });

  it('renders scene properties when scene selected', () => {
    render(<PropertyPanel project={mockProject} selectedScene={scenes[0]} />);
    expect(screen.getByText('场景属性')).toBeInTheDocument();
    expect(screen.getByDisplayValue('开场')).toBeInTheDocument();
  });

  it('calls onChange with updated project payload when title changes', () => {
    const onChange = vi.fn();
    render(<PropertyPanel project={mockProject} onChange={onChange} />);

    const input = screen.getByDisplayValue('Test');
    fireEvent.change(input, { target: { value: 'New Title' } });

    expect(onChange).toHaveBeenCalledWith({
      title: 'New Title',
    });
  });

  it('calls onChange with target_format when aspect ratio button is clicked', () => {
    const onChange = vi.fn();
    render(<PropertyPanel project={mockProject} onChange={onChange} />);

    fireEvent.click(screen.getByRole('button', { name: '9:16' }));

    expect(onChange).toHaveBeenCalledWith({
      target_format: '9:16',
    });
  });

  it('calls onProjectSave when save button is clicked', () => {
    const onProjectSave = vi.fn();
    render(<PropertyPanel project={mockProject} onProjectSave={onProjectSave} />);

    const input = screen.getByDisplayValue('Test');
    fireEvent.change(input, { target: { value: 'New Title' } });
    fireEvent.click(screen.getByRole('button', { name: /保存项目属性/ }));

    expect(onProjectSave).toHaveBeenCalledWith({ title: 'New Title' });
  });

  it('renders asset list', () => {
    render(<PropertyPanel project={mockProject} assets={mockAssets} />);
    expect(screen.getByText('shot.png')).toBeInTheDocument();
    expect(screen.getByText('bgm.mp3')).toBeInTheDocument();
  });

  it('calls onUpload when upload button is clicked', () => {
    const onUpload = vi.fn();
    render(<PropertyPanel project={mockProject} onUpload={onUpload} />);
    fireEvent.click(screen.getByRole('button', { name: /上传/ }));
    expect(onUpload).toHaveBeenCalled();
  });

  it('calls onSceneApply when apply button is clicked after editing scene', () => {
    const onSceneApply = vi.fn();
    render(<PropertyPanel project={mockProject} selectedScene={scenes[0]} onSceneApply={onSceneApply} />);

    const input = screen.getByDisplayValue('开场');
    fireEvent.change(input, { target: { value: '新开场' } });
    fireEvent.click(screen.getByRole('button', { name: '应用修改' }));

    expect(onSceneApply).toHaveBeenCalledWith({ name: '新开场', text_content: '', duration: 5 });
  });
});
