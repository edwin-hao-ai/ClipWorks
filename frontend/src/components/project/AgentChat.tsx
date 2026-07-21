'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { clsx } from 'clsx';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { AgentPlan, AgentState, Project, Scene } from '@/lib/types';
import { MessageSquare, Send, Bot, User, Pencil, Check, X, Wand2 } from 'lucide-react';

interface Message {
  role: 'user' | 'agent';
  text: string;
}

interface AgentChatProps {
  projectId: string;
  selectedSceneId?: string | null;
  scenes?: Scene[];
  mode: 'plan' | 'modify' | 'vibe';
  agentState?: AgentState;
  initialPrompt?: string;
  sourceUrl?: string;
  size?: 'sm' | 'lg';
  initialMessages?: Message[];
  onStatusChange: (status: Project['status']) => void;
  onAgentStateChange?: (state: AgentState) => void;
}

const MODIFY_QUICK_PROMPTS = [
  '更活泼一点',
  '针对年轻人',
  '把标题改成红色',
  '缩短到 15 秒',
  '换背景音乐',
];

const VIBE_QUICK_PROMPTS = [
  '生成 30 秒短视频',
  '换成 9:16 竖屏',
  '加一段开场动画',
  '用更活泼的风格',
];

const PLAN_QUICK_PROMPTS = [
  '30 秒，9:16，小红书风格，面向年轻女性',
  '15 秒，16:9，科技感产品发布',
  '60 秒，16:9，教程步骤清晰',
  '开始生成',
];

// 把后端的 402（额度不足）翻译成带计费页入口的友好提示，其它错误原样返回。
function formatAgentError(msg: string, fallback: string): string {
  if (msg.includes('402')) return '额度不足，无法继续生成。请前往 /billing 升级套餐后再试。';
  return msg || fallback;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function planToText(plan: AgentPlan | null): string {
  if (!plan) return '';
  return (
    `**${plan.title}**\n` +
    `${plan.hook ? `钩子：${plan.hook}\n` : ''}` +
    `画幅：${plan.format}，时长：${plan.duration} 秒，引擎：${plan.engine_hint}\n\n` +
    plan.scenes
      .map(
        (s, idx) =>
          `场景 ${idx + 1}（${s.start}s-${s.start + s.duration}s）：${s.description}` +
          (s.text ? ` · 文案：${s.text}` : '')
      )
      .join('\n')
  );
}

/** 从流式 JSON 片段里尽量提取 question，让用户看到思考过程而非空白 loading。 */
function extractStreamingQuestion(text: string): string | null {
  try {
    let jsonText = text;
    if (text.includes('```json')) {
      jsonText = text.split('```json')[1].split('```')[0];
    } else if (text.includes('```')) {
      jsonText = text.split('```')[1].split('```')[0];
    }
    const match = jsonText.match(/"question"\s*:\s*"((?:\\.|[^"\\])*)"/);
    if (match) {
      return match[1].replace(/\\n/g, '\n').replace(/\\"/g, '"');
    }
  } catch {
    // 片段不完整时无法解析，忽略即可。
  }
  return null;
}

/** 从流式方案 JSON 里提取可读的预览片段（标题、钩子、场景数）。 */
function extractStreamingPlanPreview(text: string): { title?: string; hook?: string; sceneCount?: number } | null {
  try {
    let jsonText = text;
    if (text.includes('```json')) {
      jsonText = text.split('```json')[1].split('```')[0];
    } else if (text.includes('```')) {
      jsonText = text.split('```')[1].split('```')[0];
    }
    const titleMatch = jsonText.match(/"title"\s*:\s*"((?:\\.|[^"\\])*)"/);
    const hookMatch = jsonText.match(/"hook"\s*:\s*"((?:\\.|[^"\\])*)"/);
    const sceneMatches = jsonText.match(/"scenes"\s*:\s*\[/);
    const sceneCount = sceneMatches ? jsonText.slice(jsonText.indexOf('[')).split('"start"').length - 1 : undefined;
    const result: { title?: string; hook?: string; sceneCount?: number } = {};
    if (titleMatch) result.title = titleMatch[1].replace(/\\n/g, ' ').replace(/\\"/g, '"');
    if (hookMatch) result.hook = hookMatch[1].replace(/\\n/g, ' ').replace(/\\"/g, '"');
    if (sceneCount && sceneCount > 0) result.sceneCount = sceneCount;
    return Object.keys(result).length > 0 ? result : null;
  } catch {
    return null;
  }
}

interface ClarifyingQuestion {
  question: string;
  why?: string;
}

function parseQuestion(text: string): ClarifyingQuestion | null {
  try {
    const block = text.includes('```json')
      ? text.split('```json')[1].split('```')[0].trim()
      : text.includes('```')
      ? text.split('```')[1].split('```')[0].trim()
      : text.trim();
    const data = JSON.parse(block);
    if (data.needs_more_info && typeof data.question === 'string') {
      return { question: data.question, why: data.why };
    }
  } catch {
    // ignore
  }
  return null;
}

export function AgentChat({
  projectId,
  selectedSceneId,
  scenes = [],
  mode,
  agentState,
  initialPrompt,
  sourceUrl,
  size = 'sm',
  initialMessages: initialMessagesProp,
  onStatusChange,
  onAgentStateChange,
}: AgentChatProps) {
  const isLg = size === 'lg';

  const initialMessages = useMemo<Message[]>(() => {
    if (initialMessagesProp && initialMessagesProp.length > 0) {
      return initialMessagesProp;
    }
    if (agentState?.messages && agentState.messages.length > 0) {
      return agentState.messages.map((m) => ({
        role: m.role === 'user' ? 'user' : 'agent',
        text: m.content,
      }));
    }
    if (mode === 'plan') {
      return [
        {
          role: 'agent',
          text: 'Hi! 我是你的 AI 导演。先和我聊聊你想做什么视频：用途、时长、画幅、风格？不够清楚的话我会先问你。',
        },
      ];
    }
    if (mode === 'vibe') {
      return [
        {
          role: 'agent',
          text: 'Hi! 我是你的 Vibe 创作助手。告诉我你想做什么样的视频，我会边想边做。',
        },
      ];
    }
    return [
      {
        role: 'agent',
        text: 'Hi! 我是你的 AI 导演。输入一句话开始创作，或点击左侧场景卡片修改某个画面。',
      },
    ];
  }, [agentState, mode, initialMessagesProp]);

  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState('');
  const [pendingPlan, setPendingPlan] = useState<AgentPlan | null>(agentState?.pending_plan || null);
  const [decisionLoading, setDecisionLoading] = useState<'approve' | 'reject' | null>(null);
  const [rejectMode, setRejectMode] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  // AbortController for the in-flight Vibe stream. A new message aborts the
  // previous one, and unmounting aborts any active stream to avoid setState
  // after teardown.
  const vibeAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      vibeAbortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText, loading, pendingPlan]);

  useEffect(() => {
    setPendingPlan(agentState?.pending_plan || null);
  }, [agentState?.pending_plan]);

  const selectedScene = useMemo(
    () => scenes.find((s) => s.id === selectedSceneId),
    [selectedSceneId, scenes]
  );

  const introducedSceneIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (selectedScene && !introducedSceneIdsRef.current.has(selectedScene.id)) {
      introducedSceneIdsRef.current.add(selectedScene.id);
      setMessages((prev) => [
        ...prev,
        {
          role: 'agent',
          text: `你选中了「${selectedScene.name}」（${formatTime(
            selectedScene.start_time
          )}-${formatTime(selectedScene.start_time + selectedScene.duration)}）。想怎么改这个场景？`,
        },
      ]);
    }
  }, [selectedScene]);

  // Auto-send the initial prompt from the launchpad when there is no prior
  // conversation history. This keeps the flow continuous: user types on the
  // home page, lands in the workspace, and immediately sees the Agent respond.
  const autoSentRef = useRef(false);
  useEffect(() => {
    if (
      !autoSentRef.current &&
      (mode === 'plan' || mode === 'vibe') &&
      initialPrompt &&
      !loading &&
      !agentState?.messages?.length
    ) {
      autoSentRef.current = true;
      setMessages((prev) => [...prev, { role: 'user', text: initialPrompt }]);
      if (mode === 'plan') {
        handlePlanStream(initialPrompt);
      } else {
        handleVibeStream(initialPrompt);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, initialPrompt, loading, agentState?.messages?.length]);

  const handlePlanStream = async (text: string) => {
    setLoading(true);
    setError(null);
    setStreamingText('');
    setPendingPlan(null);

    let currentReply = '';
    let receivedPlan: AgentPlan | null = null;

    try {
      for await (const event of api.stream(`/projects/${projectId}/agent/chat/stream`, {
        message: text,
      })) {
        if (!event || typeof event !== 'object') continue;
        if (event.type === 'token' && typeof event.text === 'string') {
          currentReply += event.text;
          setStreamingText(currentReply);
        } else if (event.type === 'plan' && event.plan) {
          receivedPlan = event.plan as AgentPlan;
          setPendingPlan(receivedPlan);
        } else if (event.type === 'done') {
          break;
        }
      }

      if (receivedPlan) {
        setMessages((prev) => [...prev, { role: 'agent', text: planToText(receivedPlan) }]);
        onStatusChange('planning');
      } else if (currentReply) {
        setMessages((prev) => [...prev, { role: 'agent', text: currentReply }]);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Agent 请求失败';
      setError(msg);
      setMessages((prev) => [...prev, { role: 'agent', text: `抱歉，我没法继续：${msg}` }]);
    } finally {
      setLoading(false);
      setStreamingText('');
    }
  };

  const handleRejectStream = async (text: string) => {
    setDecisionLoading('reject');
    setError(null);
    setStreamingText('');
    setPendingPlan(null);

    let currentReply = '';
    let receivedPlan: AgentPlan | null = null;

    try {
      for await (const event of api.stream(`/projects/${projectId}/agent/reject`, {
        message: text,
      })) {
        if (!event || typeof event !== 'object') continue;
        if (event.type === 'token' && typeof event.text === 'string') {
          currentReply += event.text;
          setStreamingText(currentReply);
        } else if (event.type === 'plan' && event.plan) {
          receivedPlan = event.plan as AgentPlan;
          setPendingPlan(receivedPlan);
        } else if (event.type === 'done') {
          break;
        }
      }

      if (receivedPlan) {
        setMessages((prev) => [...prev, { role: 'agent', text: planToText(receivedPlan) }]);
        onStatusChange('planning');
      } else if (currentReply) {
        setMessages((prev) => [...prev, { role: 'agent', text: currentReply }]);
        onStatusChange('draft');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Agent 请求失败';
      setError(msg);
      setMessages((prev) => [...prev, { role: 'agent', text: `抱歉，我没法继续：${msg}` }]);
    } finally {
      setDecisionLoading(null);
      setRejectMode(false);
      setLoading(false);
      setStreamingText('');
    }
  };

  const handleApprove = async () => {
    setDecisionLoading('approve');
    setError(null);
    try {
      await api.post(`/projects/${projectId}/agent/approve`, {});
      onStatusChange('generating');
    } catch (err) {
      const msg = formatAgentError(err instanceof Error ? err.message : '', '确认计划失败');
      setError(msg);
    } finally {
      setDecisionLoading(null);
    }
  };

  const sendModification = async (text: string) => {
    if (!text.trim() || loading) return;
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const payload: { message: string; render: boolean; scene_id?: string } = { message: text, render: true };
      if (selectedSceneId) payload.scene_id = selectedSceneId;
      const data = await api.post(`/projects/${projectId}/agent/chat`, payload);
      const reply = data.reply || '已收到你的修改要求。';
      setMessages((prev) => [...prev, { role: 'agent', text: reply }]);
      if (data.job_id) {
        onStatusChange('generating');
      }
    } catch (err) {
      const msg = formatAgentError(err instanceof Error ? err.message : '', 'Agent 请求失败');
      setError(msg);
      setMessages((prev) => [...prev, { role: 'agent', text: `抱歉，我没法应用这个修改：${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  // 用于合并 Vibe 流中的 artifact 事件，保持 AgentState 的其它字段不变。
  const agentStateRef = useRef<AgentState | undefined>(agentState);
  useEffect(() => {
    agentStateRef.current = agentState;
  }, [agentState]);

  const emitAgentState = (patch: Partial<AgentState>) => {
    const next: AgentState = {
      step: agentStateRef.current?.step || 'chatting',
      ...(agentStateRef.current || {}),
      ...patch,
    };
    agentStateRef.current = next;
    onAgentStateChange?.(next);
  };

  const handleVibeStream = async (text: string) => {
    // Cancel any previous Vibe stream before starting a new one so that stale
    // responses don't overwrite the current UI state.
    vibeAbortRef.current?.abort();
    const controller = new AbortController();
    vibeAbortRef.current = controller;

    setLoading(true);
    setError(null);
    setStreamingText('');

    let currentReply = '';

    try {
      for await (const event of api.stream(`/projects/${projectId}/agent/vibe/stream`, {
        message: text,
      }, controller.signal)) {
        if (!event || typeof event !== 'object') continue;

        switch (event.type) {
          case 'token': {
            const token = (event as { text?: string }).text;
            if (typeof token === 'string') {
              currentReply += token;
              setStreamingText(currentReply);
            }
            break;
          }
          case 'question': {
            const question = (event as { text?: string }).text;
            if (typeof question === 'string') {
              setMessages((prev) => [...prev, { role: 'agent', text: question }]);
              // The same text was also streamed as tokens; clear the
              // accumulator so it isn't appended again at stream end.
              currentReply = '';
            }
            break;
          }
          case 'job_created': {
            onStatusChange('generating');
            break;
          }
          case 'artifact': {
            const kind = (event as { kind?: string }).kind;
            const data = (event as { data?: unknown }).data;
            if (kind) {
              const payload: NonNullable<AgentState['payload']> = {
                ...(agentStateRef.current?.payload || {}),
              };
              switch (kind) {
                case 'understand':
                  payload.understand = data as NonNullable<AgentState['payload']>['understand'];
                  break;
                case 'script':
                  payload.script = data as NonNullable<AgentState['payload']>['script'];
                  break;
                case 'assets':
                  payload.assets = data as NonNullable<AgentState['payload']>['assets'];
                  break;
                case 'scenes':
                  payload.scenes = data as NonNullable<AgentState['payload']>['scenes'];
                  break;
                case 'effects':
                  payload.effects = data as NonNullable<AgentState['payload']>['effects'];
                  break;
              }
              emitAgentState({ step: kind as AgentState['step'], payload });
            }
            break;
          }
          case 'progress': {
            const step = (event as { step?: string }).step;
            if (typeof step === 'string') {
              emitAgentState({ generating_step: step as AgentState['step'] });
            }
            break;
          }
          case 'error': {
            const message = (event as { message?: string }).message;
            if (typeof message === 'string') {
              setError(formatAgentError(message, 'Vibe 创作失败'));
            }
            break;
          }
          case 'done': {
            // The backend sends { type: 'done', step: session.step }; the
            // accumulated payload is already merged via artifact events.
            const step = (event as { step?: AgentState['step'] }).step;
            if (step) {
              emitAgentState({ step });
            }
            break;
          }
        }

        if (event.type === 'done') break;
      }
      if (currentReply) {
        setMessages((prev) => [...prev, { role: 'agent', text: currentReply }]);
      }
    } catch (err) {
      // Intentional cancellation (new message or unmount) should not surface an
      // error banner; only the active stream owns the loading/UI state.
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      const msg = err instanceof Error ? err.message : 'Vibe 请求失败';
      setError(msg);
      setMessages((prev) => [...prev, { role: 'agent', text: `抱歉，Vibe 创作遇到问题：${msg}` }]);
    } finally {
      // Only clear loading if this stream is still the current one. If a newer
      // message started, it has already taken over the UI state.
      if (vibeAbortRef.current === controller) {
        setLoading(false);
        setStreamingText('');
        vibeAbortRef.current = null;
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || (mode !== 'vibe' && loading)) return;

    if (mode === 'plan') {
      if (rejectMode) {
        setMessages((prev) => [...prev, { role: 'user', text: input }]);
        handleRejectStream(input);
      } else {
        setMessages((prev) => [...prev, { role: 'user', text: input }]);
        handlePlanStream(input);
      }
      setInput('');
    } else if (mode === 'vibe') {
      setMessages((prev) => [...prev, { role: 'user', text: input }]);
      handleVibeStream(input);
      setInput('');
    } else {
      sendModification(input);
    }
  };

  const quickPrompts =
    mode === 'plan' ? PLAN_QUICK_PROMPTS : mode === 'vibe' ? VIBE_QUICK_PROMPTS : MODIFY_QUICK_PROMPTS;

  return (
    <div
      className={clsx(
        'bg-background-surface border border-border-subtle rounded-lg flex flex-col relative',
        isLg ? 'h-full rounded-2xl' : 'h-[360px]'
      )}
    >
      <div className={clsx('flex items-center shrink-0 border-b border-border-subtle', isLg ? 'gap-3 p-5' : 'gap-2 p-3')}>
        <MessageSquare className={clsx('text-brand-400', isLg ? 'w-5 h-5' : 'w-4 h-4')} />
        <span className={clsx('font-semibold', isLg ? 'text-base' : 'text-sm')}>
          {mode === 'plan' ? 'AI 导演 · 规划' : mode === 'vibe' ? 'Vibe 创作' : 'AI 导演 · 修改'}
        </span>
        {selectedScene && (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-brand-900/40 text-brand-400 border border-brand-900/60 flex items-center gap-1">
            <Pencil className="w-3 h-3" /> {selectedScene.name}
          </span>
        )}
      </div>

      <div
        className={clsx(
          'flex-1 overflow-y-auto min-h-0',
          isLg ? 'space-y-4 p-5 pr-6 text-base' : 'space-y-3 p-3 pr-4 text-sm'
        )}
      >
        {messages.map((m, idx) => {
          const question = m.role === 'agent' && mode === 'plan' ? parseQuestion(m.text) : null;
          return (
            <div key={idx} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <div
                className={clsx(
                  'rounded-full flex items-center justify-center shrink-0',
                  isLg ? 'w-9 h-9' : 'w-7 h-7',
                  m.role === 'agent' ? 'bg-brand-900/50 text-brand-400' : 'bg-background-elevated text-content-secondary'
                )}
              >
                {m.role === 'agent' ? (
                  <Bot className={isLg ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
                ) : (
                  <User className={isLg ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
                )}
              </div>
              {question ? (
                <div
                  className={clsx(
                    'bg-brand-900/20 border border-brand-500/30 rounded-lg',
                    isLg ? 'max-w-[85%] p-4 rounded-xl' : 'max-w-[90%] p-3'
                  )}
                >
                  <div
                    className={clsx(
                      'flex items-center font-semibold text-brand-400 mb-1.5',
                      isLg ? 'text-sm gap-2 mb-2' : 'text-xs gap-1.5 mb-1.5'
                    )}
                  >
                    <MessageSquare className={isLg ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
                    AI 导演的问题
                  </div>
                  <p className={clsx('text-content-primary mb-1.5', isLg ? 'text-base' : 'text-sm')}>
                    {question.question}
                  </p>
                  {question.why && (
                    <p className={clsx('text-content-tertiary', isLg ? 'text-sm' : 'text-xs')}>
                      {question.why}
                    </p>
                  )}
                </div>
              ) : (
                <div
                  className={clsx(
                    'rounded-lg whitespace-pre-line break-words',
                    isLg ? 'max-w-[80%] text-base px-4 py-3' : 'max-w-[85%] text-sm px-3 py-2',
                    m.role === 'agent'
                      ? 'bg-background-elevated text-content-secondary border border-border-subtle'
                      : 'bg-brand-600 text-content-inverse'
                  )}
                >
                  {m.text}
                </div>
              )}
            </div>
          );
        })}

        {streamingText && (
          <div className="flex gap-2">
            <div
              className={clsx(
                'rounded-full bg-brand-900/50 text-brand-400 flex items-center justify-center shrink-0',
                isLg ? 'w-9 h-9' : 'w-7 h-7'
              )}
            >
              <Bot className={isLg ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
            </div>
            <div
              className={clsx(
                'rounded-lg bg-background-elevated text-content-secondary border border-border-subtle whitespace-pre-line break-words',
                isLg ? 'max-w-[80%] text-base px-4 py-3' : 'max-w-[85%] text-sm px-3 py-2'
              )}
            >
              {(() => {
                const isJsonLike =
                  streamingText.includes('```json') ||
                  streamingText.trim().startsWith('{') ||
                  streamingText.trim().startsWith('```');
                if (!isJsonLike) return streamingText;
                const question = extractStreamingQuestion(streamingText);
                if (question) {
                  return <span className="italic text-content-tertiary">AI 在思考：{question}</span>;
                }
                const planPreview = extractStreamingPlanPreview(streamingText);
                if (planPreview) {
                  return (
                    <span className="italic text-content-tertiary">
                      AI 正在规划方案
                      {planPreview.title ? `：${planPreview.title}` : ''}
                      {planPreview.hook ? ` · ${planPreview.hook}` : ''}
                      {planPreview.sceneCount ? ` · ${planPreview.sceneCount} 个场景` : ''}
                      …
                    </span>
                  );
                }
                return <span className="italic text-content-tertiary">AI 正在组织方案…</span>;
              })()}
            </div>
          </div>
        )}

        {loading && !streamingText && (
          <div className="flex gap-2">
            <div
              className={clsx(
                'rounded-full bg-brand-900/50 text-brand-400 flex items-center justify-center shrink-0',
                isLg ? 'w-9 h-9' : 'w-7 h-7'
              )}
            >
              <Bot className={isLg ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
            </div>
            <div
              className={clsx(
                'bg-background-elevated border border-border-subtle text-content-secondary rounded-lg flex items-center gap-2',
                isLg ? 'px-4 py-3 text-base' : 'px-3 py-2 text-sm'
              )}
            >
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.1s]" />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.2s]" />
              <span className={isLg ? 'text-sm' : 'text-xs'}>
                {sourceUrl ? 'AI 正在读取网页并分析素材…' : 'AI 正在思考…'}
              </span>
            </div>
          </div>
        )}

        {error && (
          <div className="text-xs text-error bg-error/10 border border-error/20 px-3 py-2 rounded-lg">
            {error}
          </div>
        )}

        {pendingPlan && mode === 'plan' && !rejectMode && (
          <div className="flex gap-2">
            <div
              className={clsx(
                'rounded-full bg-brand-900/50 text-brand-400 flex items-center justify-center shrink-0',
                isLg ? 'w-9 h-9' : 'w-7 h-7'
              )}
            >
              <Wand2 className={isLg ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
            </div>
            <div
              className={clsx(
                'flex-1 border border-brand-500/30 rounded-lg bg-brand-900/10',
                isLg ? 'p-4 rounded-xl max-w-[85%]' : 'p-3 max-w-[90%]'
              )}
            >
              <div className={clsx('flex items-center gap-2 text-brand-400 mb-2', isLg ? 'mb-3' : 'mb-2')}>
                <span className={clsx('font-semibold', isLg ? 'text-sm' : 'text-xs')}>方案已就绪</span>
                <span className="text-content-tertiary">·</span>
                <span className={clsx('text-content-tertiary', isLg ? 'text-sm' : 'text-xs')}>
                  确认后进入生成
                </span>
              </div>
              <div className="space-y-2 mb-3">
                <h4 className={clsx('font-semibold text-content-primary', isLg ? 'text-base' : 'text-sm')}>
                  {pendingPlan.title}
                </h4>
                {pendingPlan.hook && (
                  <p className={clsx('text-content-secondary', isLg ? 'text-sm' : 'text-xs')}>
                    {pendingPlan.hook}
                  </p>
                )}
                <div className="flex flex-wrap gap-2">
                  {[
                    pendingPlan.format,
                    `${pendingPlan.duration} 秒`,
                    pendingPlan.engine_hint,
                  ].map((label) => (
                    <span
                      key={label}
                      className={clsx(
                        'px-2 py-0.5 rounded-full bg-background-elevated border border-border-subtle text-content-secondary',
                        isLg ? 'text-xs' : 'text-[10px]'
                      )}
                    >
                      {label}
                    </span>
                  ))}
                </div>
                <div className={clsx('space-y-1.5', isLg ? 'mt-3' : 'mt-2')}>
                  {pendingPlan.scenes.map((s, idx) => (
                    <div
                      key={idx}
                      className={clsx(
                        'text-content-secondary bg-background-elevated/40 rounded border border-border-subtle/50',
                        isLg ? 'text-sm p-2.5' : 'text-xs p-2'
                      )}
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-content-primary">场景 {idx + 1}</span>
                        <span className="text-content-tertiary">
                          ({s.start}s–{s.start + s.duration}s)
                        </span>
                      </div>
                      <p className="mt-1">{s.description}</p>
                      {s.text && <p className="mt-1 text-brand-400">“{s.text}”</p>}
                    </div>
                  ))}
                </div>
                {pendingPlan.assets_needed.length > 0 && (
                  <div className={clsx('text-content-tertiary', isLg ? 'text-sm' : 'text-xs')}>
                    需要素材：{pendingPlan.assets_needed.join('、')}
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  size={isLg ? 'md' : 'sm'}
                  className="flex-1"
                  onClick={handleApprove}
                  disabled={decisionLoading === 'approve'}
                >
                  {decisionLoading === 'approve' ? (
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <span className="flex items-center gap-1.5">
                      <Check className="w-3.5 h-3.5" />
                      确认生成
                    </span>
                  )}
                </Button>
                <Button
                  variant="secondary"
                  size={isLg ? 'md' : 'sm'}
                  className="flex-1"
                  onClick={() => setRejectMode(true)}
                  disabled={decisionLoading !== null}
                >
                  <X className="w-3.5 h-3.5" />
                  再改改
                </Button>
              </div>
            </div>
          </div>
        )}

        {rejectMode && (
          <div
            className={clsx(
              'text-content-secondary bg-background-elevated border border-border-subtle rounded-lg px-3 py-2',
              isLg ? 'text-sm' : 'text-xs'
            )}
          >
            告诉我哪里需要调整，AI 会重新规划方案。
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div
        className={clsx(
          'shrink-0 border-t border-border-subtle bg-background-surface z-10',
          isLg ? 'p-5 space-y-3' : 'p-3 space-y-2'
        )}
      >
        <div className={clsx('flex flex-wrap', isLg ? 'gap-2' : 'gap-1.5')}>
          {quickPrompts.map((p) => (
            <button
              key={p}
              onClick={() => {
                if (mode === 'plan') {
                  setMessages((prev) => [...prev, { role: 'user', text: p }]);
                  if (rejectMode) {
                    handleRejectStream(p);
                  } else {
                    handlePlanStream(p);
                  }
                } else if (mode === 'vibe') {
                  setMessages((prev) => [...prev, { role: 'user', text: p }]);
                  handleVibeStream(p);
                } else {
                  sendModification(p);
                }
              }}
              disabled={(mode !== 'vibe' && loading) || decisionLoading !== null}
              className={clsx(
                'rounded-full bg-background-elevated border border-border-subtle text-content-secondary hover:text-content-primary hover:border-border-default transition-colors disabled:opacity-50',
                isLg ? 'text-sm px-3 py-1.5' : 'text-xs px-2 py-1'
              )}
            >
              {p}
            </button>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              rejectMode
                ? '你想调整哪里？'
                : selectedScene
                ? `修改「${selectedScene.name}」…`
                : mode === 'plan'
                ? '描述你想做的视频…'
                : mode === 'vibe'
                ? '描述你的 Vibe 视频想法…'
                : '输入创作或修改指令…'
            }
            disabled={(mode !== 'vibe' && loading) || decisionLoading !== null}
            className={clsx(
              'flex-1 min-w-0 bg-background-elevated border border-border-subtle text-content-primary placeholder-content-tertiary focus:outline-none focus:border-brand-500 disabled:opacity-50',
              isLg ? 'px-4 py-3 text-base rounded-lg' : 'px-3 py-2 text-sm rounded-md'
            )}
          />
          <Button type="submit" disabled={(mode !== 'vibe' && loading) || !input.trim() || decisionLoading !== null} size={isLg ? 'md' : 'sm'}>
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
