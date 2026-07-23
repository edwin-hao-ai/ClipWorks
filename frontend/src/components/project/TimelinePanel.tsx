'use client';

import { useState } from 'react';
import Link from 'next/link';
import { clsx } from 'clsx';
import { Composition } from '@/lib/types';

interface TimelinePanelProps {
  composition: Composition | null;
}

export function TimelinePanel({ composition }: TimelinePanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  if (!composition) return null;

  const tracks = composition.tracks || [];

  return (
    <div className={clsx('h-full bg-background-surface border-l border-border-subtle flex flex-col', collapsed && 'w-12')}
      style={{ width: collapsed ? 48 : 280 }}>
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-between px-3 py-2 border-b border-border-subtle text-sm font-medium"
      >
        {!collapsed && <span>Timeline</span>}
        <span>{collapsed ? '←' : '→'}</span>
      </button>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3 text-sm">
          {tracks.map((track) => (
            <div key={track.id}>
              <div className="text-content-tertiary text-xs mb-1 capitalize">{track.type} Track</div>
              <div className="space-y-1">
                {track.clips.map((clip) => (
                  <div
                    key={clip.id}
                    className="h-7 rounded px-2 flex items-center bg-background-elevated border border-border-subtle truncate"
                    title={clip.text_content || clip.asset_id || 'clip'}
                  >
                    {clip.text_content || clip.asset_id || 'clip'}
                  </div>
                ))}
              </div>
            </div>
          ))}
          <Link
            href={`/projects/${composition.project_id}/editor`}
            className="block text-center text-xs px-3 py-2 rounded bg-background-elevated border border-border-subtle hover:border-border-default"
          >
            打开高级编辑器 →
          </Link>
        </div>
      )}
    </div>
  );
}
