import React, { useEffect, useRef } from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  Video,
  interpolate,
  useCurrentFrame,
} from "remotion";

// Local CJK font stack. The renderer Docker image installs fonts-noto-cjk,
// and macOS/Windows developers get reasonable fallbacks.
const FONT_STACK =
  "'Noto Sans CJK SC', 'PingFang SC', 'Microsoft YaHei', sans-serif";

// 根据 clip 的 visual/style 文本判断应启用哪种氛围动效。
function visualFlavor(visual?: string): string {
  const v = (visual || "").toLowerCase();
  if (/代码|数据|git|tech|hud|科技|编程|markdown|编辑器|搜索|ai|问答|对话|chat|智能/.test(v))
    return "tech";
  if (/粒子|光|glow|neon|闪耀|星空|宇宙|premium|奢华|金/.test(v)) return "particles";
  if (/火箭|起飞|发布|速度|rocket|launch|fast/.test(v)) return "speed";
  if (/混乱|文档|文件|堆叠|chaos|files|mess/.test(v)) return "chaos";
  if (/暖|日出|橙|sun|warm|自然|绿|forest/.test(v)) return "warm";
  return "default";
}

// 胶片颗粒 + 暗角叠加，提升成片质感。
const GrainOverlay: React.FC<{ width: number; height: number }> = ({ width, height }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frame = useCurrentFrame();
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = width;
    canvas.height = height;
    const imageData = ctx.createImageData(width, height);
    const data = imageData.data;
    for (let i = 0; i < data.length; i += 4) {
      const v = Math.random() * 35;
      data[i] = v;
      data[i + 1] = v;
      data[i + 2] = v;
      data[i + 3] = 18;
    }
    ctx.putImageData(imageData, 0, 0);
  }, [width, height, frame]);
  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{ position: "absolute", inset: 0, opacity: 0.35, pointerEvents: "none", zIndex: 900, mixBlendMode: "overlay" }}
    />
  );
};

const Vignette: React.FC<{ width: number; height: number }> = ({ width, height }) => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      pointerEvents: "none",
      zIndex: 899,
      background: `radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55) 100%)`,
    }}
  />
);

// 用 Canvas 绘制场景级氛围动效，避免静态图片像幻灯片。
const AmbientCanvas: React.FC<{
  flavor: string;
  width: number;
  height: number;
  brandColor: string;
}> = ({ flavor, width, height, brandColor }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frame = useCurrentFrame();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = width;
    canvas.height = height;
    ctx.clearRect(0, 0, width, height);

    const t = frame / 30;

    const hexToRgb = (hex: string) => {
      const clean = hex.replace("#", "");
      const bigint = parseInt(clean.length === 3 ? clean.split("").map((c) => c + c).join("") : clean, 16);
      return { r: (bigint >> 16) & 255, g: (bigint >> 8) & 255, b: bigint & 255 };
    };
    const rgb = hexToRgb(brandColor);

    // 背景光晕
    const glowGradient = ctx.createRadialGradient(width * 0.3, height * 0.7, 0, width * 0.3, height * 0.7, width * 0.6);
    glowGradient.addColorStop(0, `rgba(${rgb.r},${rgb.g},${rgb.b},0.12)`);
    glowGradient.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = glowGradient;
    ctx.fillRect(0, 0, width, height);

    if (flavor === "tech") {
      // 网格
      ctx.strokeStyle = `rgba(${rgb.r},${rgb.g},${rgb.b},0.10)`;
      ctx.lineWidth = 1;
      const step = 56;
      for (let x = 0; x <= width; x += step) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, height); ctx.stroke();
      }
      for (let y = 0; y <= height; y += step) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke();
      }
      // 数字雨
      ctx.fillStyle = brandColor;
      for (let i = 0; i < 50; i++) {
        const x = ((i * 73) % width);
        const y = ((i * 53 + frame * (2 + (i % 4))) % height);
        const s = 2 + (i % 4);
        ctx.globalAlpha = 0.2 + 0.4 * Math.sin(t * 2 + i);
        ctx.fillRect(x, y, s, s * 3);
      }
      ctx.globalAlpha = 1;
      // 扫描线
      ctx.fillStyle = `rgba(${rgb.r},${rgb.g},${rgb.b},0.08)`;
      const scanY = (frame * 5) % height;
      ctx.fillRect(0, scanY, width, 8);
    } else if (flavor === "particles" || flavor === "default") {
      const count = flavor === "particles" ? 55 : 22;
      for (let i = 0; i < count; i++) {
        const x = ((i * 137 + frame * (0.4 + (i % 3) * 0.2)) % width);
        const y = ((i * 97 + frame * 0.25) % height);
        const r = flavor === "particles" ? 1.5 + (i % 6) : 1 + (i % 3);
        const alpha = flavor === "particles" ? 0.2 + 0.6 * Math.abs(Math.sin(t + i)) : 0.1 + 0.25 * Math.abs(Math.sin(t + i));
        ctx.beginPath();
        ctx.fillStyle = brandColor;
        ctx.globalAlpha = alpha;
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      if (flavor === "particles") {
        // lens flare
        const fx = width * 0.7 + Math.sin(t * 0.5) * 80;
        const fy = height * 0.3 + Math.cos(t * 0.4) * 60;
        const flare = ctx.createRadialGradient(fx, fy, 0, fx, fy, width * 0.25);
        flare.addColorStop(0, `rgba(${rgb.r},${rgb.g},${rgb.b},0.25)`);
        flare.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = flare;
        ctx.filter = "blur(40px)";
        ctx.beginPath(); ctx.arc(fx, fy, width * 0.25, 0, Math.PI * 2); ctx.fill();
        ctx.filter = "none";
      }
    } else if (flavor === "speed") {
      ctx.strokeStyle = "rgba(255,255,255,0.10)";
      ctx.lineWidth = 2;
      for (let i = 0; i < 30; i++) {
        const x = ((i * 83) % width);
        const y = ((frame * (12 + i % 10) + i * 60) % (height + 240)) - 120;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x, y + 70 + i * 5);
        ctx.stroke();
      }
      // shockwave
      const cx = width / 2, cy = height / 2;
      const wave = (frame % 75) / 75;
      ctx.strokeStyle = brandColor;
      ctx.globalAlpha = 0.6 * (1 - wave);
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, 80 + wave * Math.max(width, height) * 1.2, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 1;
    } else if (flavor === "chaos") {
      ctx.strokeStyle = "rgba(255,255,255,0.12)";
      for (let i = 0; i < 22; i++) {
        const x = width * 0.05 + ((i * 103) % (width * 0.85));
        const y = height * 0.05 + ((i * 79) % (height * 0.75));
        const rot = Math.sin(t + i) * 0.18;
        const w = width * 0.04;
        const h = width * 0.055;
        ctx.save();
        ctx.translate(x + w / 2, y + h / 2);
        ctx.rotate(rot);
        ctx.strokeRect(-w / 2, -h / 2, w, h);
        ctx.restore();
      }
    } else if (flavor === "warm") {
      for (let i = 0; i < 14; i++) {
        const x = ((i * 151 + t * 10) % width);
        const y = ((i * 113 + t * 8) % height);
        const size = 60 + (i % 70);
        const orb = ctx.createRadialGradient(x, y, 0, x, y, size);
        orb.addColorStop(0, "rgba(255,160,80,0.30)");
        orb.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = orb;
        ctx.filter = "blur(20px)";
        ctx.beginPath(); ctx.arc(x, y, size, 0, Math.PI * 2); ctx.fill();
        ctx.filter = "none";
      }
    }
  }, [flavor, width, height, frame, brandColor]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        position: "absolute",
        inset: 0,
        width,
        height,
        opacity: 0.6,
        pointerEvents: "none",
        zIndex: 1,
      }}
    />
  );
};

// 镜头级动效（可商用感的低成本来源）：每个场景首/尾各做一次透明度缓动，
// 静态图片做极慢的推镜（Ken Burns），文字做轻微上浮入场。全部基于 Remotion
// interpolate，确定性、无额外依赖；fade 走黑而非真叠化，避免改变场景时长。
// 场景转场由 clip.style.transition 驱动（fade | slide | zoom），与 Agent 富方案
// schema 对齐；未声明时退回 fade，旧合成向后兼容。
const SCENE_FADE_FRAMES = 12;

function sceneOpacity(frame: number, duration: number): number {
  const fadeIn = interpolate(frame, [0, SCENE_FADE_FRAMES], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [Math.max(0, duration - SCENE_FADE_FRAMES), duration],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return Math.min(fadeIn, fadeOut);
}

// 场景入/出场转场：入场 12 帧完成，出场反向（slide 右进左出，zoom 由大收小再放大出）。
// 返回的 transform / clipPath 只应挂在「本身就是绝对定位」的元素上，绝不套外层容器，
// 否则 transform 会改写 left/top 的定位基准（见下方组件注释）。
function sceneTransition(
  frame: number,
  duration: number,
  transition?: string
): { opacity: number; transform: string; clipPath?: string } {
  const opacity = sceneOpacity(frame, duration);
  const t = String(transition || "fade").toLowerCase();
  const enter = interpolate(frame, [0, SCENE_FADE_FRAMES], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exit = interpolate(
    frame,
    [Math.max(0, duration - SCENE_FADE_FRAMES), duration],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  if (t === "slide") {
    const x = (1 - enter) * 10 - exit * 10;
    return { opacity, transform: `translateX(${x}%)` };
  }
  if (t === "zoom") {
    const scale = 1.14 - enter * 0.14 + exit * 0.08;
    return { opacity, transform: `scale(${scale})` };
  }
  if (t === "wipe") {
    const enterClip = interpolate(frame, [0, SCENE_FADE_FRAMES], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    const exitClip = interpolate(frame, [Math.max(0, duration - SCENE_FADE_FRAMES), duration], [100, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    return { opacity: 1, transform: "", clipPath: `inset(0 ${100 - (exit ? exitClip : enterClip)}% 0 0)` };
  }
  if (t === "mask") {
    const enterCircle = interpolate(frame, [0, SCENE_FADE_FRAMES], [0, 150], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    const exitCircle = interpolate(frame, [Math.max(0, duration - SCENE_FADE_FRAMES), duration], [150, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    return { opacity: 1, transform: "", clipPath: `circle(${(exit ? exitCircle : enterCircle)}% at 50% 50%)` };
  }
  if (t === "glitch") {
    const skew = enter < 1 ? (1 - enter) * 8 : exit > 0 ? exit * -8 : 0;
    return { opacity, transform: `skewX(${skew}deg) translateX(${(1 - enter) * 4 - exit * 4}%)` };
  }
  return { opacity, transform: "" };
}

// 注意：opacity 不会为绝对定位子元素建立新的包含块，但 transform 会。
// 因此所有 transform/opacity 都直接合并到「本身就是绝对定位」的那个元素
// （Img/Video/文字 div/overlay div）的 style 上，绝不在外层套一个带 transform
// 的容器，否则会改写 left/top 的定位基准、把画面挤错位。

const KenBurnsImg: React.FC<{
  src: string;
  layoutStyle: React.CSSProperties;
  duration: number;
}> = ({ src, layoutStyle, duration }) => {
  const frame = useCurrentFrame();
  const opacity = sceneOpacity(frame, duration);
  const progress = interpolate(frame, [0, duration], [0, 1], {
    extrapolateRight: "clamp",
  });
  // 更显著的推镜 + 漂移 + 轻微旋转，让静态素材图远离「幻灯片」感。
  const scale = 1.05 + progress * 0.12;
  const driftX = Math.sin(progress * Math.PI * 0.8) * 36;
  const driftY = Math.cos(progress * Math.PI * 0.6) * 22;
  const rotate = (progress - 0.5) * 1.2;
  return (
    <Img
      src={src}
      style={{
        ...layoutStyle,
        opacity,
        transform: `scale(${scale}) translate(${driftX}px, ${driftY}px) rotate(${rotate}deg)`,
        transformOrigin: "center",
      }}
    />
  );
};

const KenBurnsVideo: React.FC<{
  src: string;
  layoutStyle: React.CSSProperties;
  duration: number;
}> = ({ src, layoutStyle, duration }) => {
  const frame = useCurrentFrame();
  const opacity = sceneOpacity(frame, duration);
  const scale = interpolate(frame, [0, duration], [1, 1.04], {
    extrapolateRight: "clamp",
  });
  return (
    <Video
      src={src}
      style={{
        ...layoutStyle,
        opacity,
        transform: `scale(${scale})`,
        transformOrigin: "center",
      }}
    />
  );
};

const MotionText: React.FC<{
  layoutStyle: React.CSSProperties;
  duration: number;
  text: string;
  transition?: string;
  brandColor?: string;
}> = ({ layoutStyle, duration, text, transition, brandColor }) => {
  const frame = useCurrentFrame();
  const { opacity, transform } = sceneTransition(frame, duration, transition);
  // 更生动的文字入场：上滑 + 模糊消除 + 轻微缩放。
  const enter = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fallbackTransform = `translateY(${(1 - enter) * 36}px) scale(${0.96 + enter * 0.04})`;
  // 品牌色呼吸光晕，让标题更有张力。
  const glow = 8 + 6 * Math.sin((frame / 30) * 2);
  const textShadow = brandColor
    ? `0 4px 28px rgba(0,0,0,0.55), 0 0 ${glow}px ${brandColor}44`
    : "0 4px 28px rgba(0,0,0,0.55)";
  return (
    <div
      style={{
        ...layoutStyle,
        opacity,
        filter: `blur(${(1 - enter) * 8}px)`,
        transform: transform || fallbackTransform,
        transformOrigin: "center",
        textShadow,
      }}
    >
      {text}
    </div>
  );
};

const MotionOverlay: React.FC<{
  layoutStyle: React.CSSProperties;
  duration: number;
  transition?: string;
  children: React.ReactNode;
}> = ({ layoutStyle, duration, transition, children }) => {
  const frame = useCurrentFrame();
  const { opacity, transform } = sceneTransition(frame, duration, transition);
  return (
    <div
      style={{
        ...layoutStyle,
        opacity,
        ...(transform ? { transform, transformOrigin: "center" } : {}),
      }}
    >
      {children}
    </div>
  );
};

// 底部信息条（lower-third）：独立于主文案的绝对定位元素，与文字 clip 同属一个
// Sequence，随场景同生共灭；深色半透明底 + 品牌色左边线，自己走场景淡入淡出。
// 刻意不放进 MotionText 子级——父元素的 transform 会改写它的绝对定位基准。
const LowerThird: React.FC<{
  text: string;
  duration: number;
  brandColor: string;
  canvasWidth: number;
  canvasHeight: number;
  scale: number;
}> = ({ text, duration, brandColor, canvasWidth, canvasHeight, scale }) => {
  const frame = useCurrentFrame();
  const opacity = sceneOpacity(frame, duration);
  return (
    <div
      style={{
        position: "absolute",
        left: Math.round(canvasWidth * 0.04),
        bottom: Math.round(canvasHeight * 0.06),
        maxWidth: Math.round(canvasWidth * 0.6),
        padding: `${Math.round(14 * scale)}px ${Math.round(28 * scale)}px`,
        background: "rgba(8,10,18,0.72)",
        borderLeft: `${Math.max(4, Math.round(6 * scale))}px solid ${brandColor}`,
        borderRadius: Math.round(8 * scale),
        color: "#ffffff",
        fontSize: Math.round(38 * scale),
        fontFamily: FONT_STACK,
        fontWeight: 600,
        textShadow: "0 1px 8px rgba(0,0,0,0.6)",
        opacity,
        zIndex: 50,
      }}
    >
      {text}
    </div>
  );
};

interface Position {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface Clip {
  id?: string;
  start_time: number;
  duration: number;
  asset_id?: string;
  position?: Position;
  style?: Record<string, any>;
  text_content?: string;
}

interface Track {
  type: string;
  index: number;
  name?: string;
  clips: Clip[];
}

function getBackgroundClip(clips: any[]) {
  return (
    clips.find((c) => c.trackType === "overlay") ||
    clips.find((c) => c.trackType === "video" || c.trackType === "image") ||
    clips[0]
  );
}

// 按素材真实类型（URL 扩展名）决定用 <Img>/<Video>/<Audio>，而不是盲目相信 track.type。
// 原因：AI 时间线常把图片素材放在 type="video" 的轨道上，若按 track.type 渲染 <Video>
// 去加载一张 .png，会解码失败、画面为空（之前的「渐变块」就是这么来的）。
type MediaKind = "image" | "video" | "audio";
function mediaKind(src?: string, trackType?: string): MediaKind {
  if (src) {
    const s = src.toLowerCase().split("?")[0];
    if (/\.(png|jpe?g|webp|gif|bmp|svg)$/.test(s)) return "image";
    if (/\.(mp4|webm|mov|m4v|ogv)$/.test(s)) return "video";
    if (/\.(mp3|ogg|wav|aac|m4a|opus)$/.test(s)) return "audio";
  }
  if (trackType === "image" || trackType === "audio") return trackType;
  return "video";
}

function inferBackgroundStyle(clip: any): React.CSSProperties {
  const style = clip?.style || {};
  if (style.background) {
    return { background: style.background };
  }
  if (style.backgroundColor) {
    return { backgroundColor: style.backgroundColor };
  }
  if (style.visual) {
    const visual = String(style.visual).toLowerCase();
    if (visual.includes("科技") || visual.includes("tech") || visual.includes("hud")) {
      return {
        background: "radial-gradient(ellipse at center, #0a1a2a 0%, #020203 100%)",
      };
    }
    if (visual.includes("粒子") || visual.includes("particle")) {
      return {
        background: "radial-gradient(ellipse at center, #0f172a 0%, #000 100%)",
      };
    }
    if (visual.includes("光") || visual.includes("glow") || visual.includes("neon")) {
      return {
        background: "radial-gradient(circle at center, #1a103c 0%, #000 100%)",
      };
    }
  }
  return {
    background: "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
  };
}

function buildTextStyle(clip: Clip, scale: number): React.CSSProperties {
  const style = clip.style || {};
  const pos = clip.position || { x: 0, y: 0, width: 1920, height: 1080 };
  return {
    position: "absolute",
    left: pos.x * scale,
    top: pos.y * scale,
    width: pos.width * scale,
    height: pos.height * scale,
    display: "flex",
    alignItems: "center",
    justifyContent:
      style.textAlign === "left"
        ? "flex-start"
        : style.textAlign === "right"
        ? "flex-end"
        : "center",
    textAlign: (style.textAlign as any) || "center",
    color: style.color || "#ffffff",
    fontSize: (style.fontSize || 64) * scale,
    fontFamily: style.fontFamily || FONT_STACK,
    fontWeight: style.fontWeight || "bold",
    textShadow: style.textShadow || "0 2px 20px rgba(0,0,0,0.5)",
    padding: 40 * scale,
    boxSizing: "border-box",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  };
}

function buildMediaStyle(clip: Clip, scale: number): React.CSSProperties {
  const style = clip.style || {};
  const pos = clip.position || { x: 0, y: 0, width: 1920, height: 1080 };
  return {
    position: "absolute",
    left: pos.x * scale,
    top: pos.y * scale,
    width: pos.width * scale,
    height: pos.height * scale,
    objectFit: style.objectFit || "cover",
  };
}

function buildOverlayStyle(clip: Clip, scale: number): React.CSSProperties {
  const style = clip.style || {};
  const pos = clip.position || { x: 0, y: 0, width: 1920, height: 1080 };
  return {
    position: "absolute",
    left: pos.x * scale,
    top: pos.y * scale,
    width: pos.width * scale,
    height: pos.height * scale,
    background: style.background || style.backgroundColor,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  };
}

function computeContentScale(
  clips: any[],
  canvasWidth: number,
  canvasHeight: number
): number {
  if (!clips.length) return 1;
  const maxX = Math.max(
    ...clips.map((c) => {
      const p = c.position || { x: 0, y: 0, width: canvasWidth, height: canvasHeight };
      return p.x + p.width;
    })
  );
  const maxY = Math.max(
    ...clips.map((c) => {
      const p = c.position || { x: 0, y: 0, width: canvasWidth, height: canvasHeight };
      return p.y + p.height;
    })
  );
  if (maxX <= canvasWidth && maxY <= canvasHeight) return 1;
  const scaleX = canvasWidth / maxX;
  const scaleY = canvasHeight / maxY;
  return Math.min(scaleX, scaleY);
}

const FPS = 30;

export const GenericComp: React.FC<{
  composition: {
    width?: number;
    height?: number;
    duration?: number;
    tracks?: Track[];
    metadata?: { brand_color?: string; brand_font?: string };
  };
  assets?: Record<string, string>;
}> = ({ composition, assets }) => {
  const tracks = composition.tracks || [];
  const canvasWidth = composition.width || 1920;
  const canvasHeight = composition.height || 1080;
  // 品牌套件：品牌色（默认 ClipWorks 青，可在 composition.metadata.brand_color 覆盖），
  // 让每条片子带统一的品牌色点缀（底部色条 + 角标），而非通用白字。
  const brandColor = composition.metadata?.brand_color || "#00E5FF";

  const allClips = tracks.flatMap((t) =>
    (t.clips || []).map((c) => ({ ...c, trackType: t.type }))
  );
  const bgClip = getBackgroundClip(allClips);
  const scale = computeContentScale(allClips, canvasWidth, canvasHeight);

  // 根据当前帧找到正在播放的视觉 clip，用它决定氛围动效 flavor。
  const frame = useCurrentFrame();
  const currentTime = frame / FPS;
  const activeVisualClip = allClips
    .filter((c) => ["image", "video", "overlay"].includes(c.trackType))
    .find((c) => {
      const start = c.start_time || 0;
      const end = start + (c.duration || 5);
      return currentTime >= start && currentTime < end;
    });
  const activeFlavor = visualFlavor(
    activeVisualClip?.style?.visual ||
      activeVisualClip?.style?.description ||
      activeVisualClip?.text_content ||
      bgClip?.style?.visual
  );

  // lower-third 去重键：LLM 常把 lower_third 写进视觉 clip 的 style，同时再生成一个
  // 内容相同的独立小文本 clip。视觉 clip 的 lower_third 由 LowerThird 组件统一渲染，
  // 内容完全相同的文本 clip 视为重复、跳过，避免同一角标叠两次。
  const visualLowerThirdKeys = new Set(
    allClips
      .filter(
        (c) =>
          (c.trackType === "image" || c.trackType === "video") &&
          c.style?.lower_third
      )
      .map(
        (c) =>
          `${Math.round((c.start_time || 0) * 10)}::${String(c.style.lower_third).trim()}`
      )
  );

  const renderLowerThird = (clip: Clip, durationFrames: number) =>
    clip.style?.lower_third ? (
      <LowerThird
        text={String(clip.style.lower_third)}
        duration={durationFrames}
        brandColor={brandColor}
        canvasWidth={canvasWidth}
        canvasHeight={canvasHeight}
        scale={scale}
      />
    ) : null;

  return (
    <AbsoluteFill style={inferBackgroundStyle(bgClip)}>
      {/* Ambient motion graphics so static images don't feel like a slideshow. */}
      <AmbientCanvas
        flavor={activeFlavor}
        width={canvasWidth}
        height={canvasHeight}
        brandColor={brandColor}
      />
      <Vignette width={canvasWidth} height={canvasHeight} />
      <GrainOverlay width={canvasWidth} height={canvasHeight} />

      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: canvasWidth,
          height: canvasHeight,
          transformOrigin: "top left",
        }}
      >
        {tracks.map((track) =>
          track.clips.map((clip) => {
            const startFrame = Math.max(0, Math.round(clip.start_time * FPS));
            const durationFrames = Math.max(
              1,
              Math.round(clip.duration * FPS)
            );
            const key = clip.id || `${track.type}-${startFrame}`;
            const src = clip.asset_id ? assets?.[clip.asset_id] : undefined;
            const kind = mediaKind(src, track.type);

            if (src && kind === "image") {
              return (
                <Sequence
                  key={key}
                  from={startFrame}
                  durationInFrames={durationFrames}
                >
                  <KenBurnsImg
                    src={src}
                    layoutStyle={buildMediaStyle(clip, scale)}
                    duration={durationFrames}
                  />
                  {renderLowerThird(clip, durationFrames)}
                </Sequence>
              );
            }

            if (src && kind === "video") {
              return (
                <Sequence
                  key={key}
                  from={startFrame}
                  durationInFrames={durationFrames}
                >
                  <KenBurnsVideo
                    src={src}
                    layoutStyle={buildMediaStyle(clip, scale)}
                    duration={durationFrames}
                  />
                  {renderLowerThird(clip, durationFrames)}
                </Sequence>
              );
            }

            if (src && kind === "audio") {
              return (
                <Sequence
                  key={key}
                  from={startFrame}
                  durationInFrames={durationFrames}
                >
                  <Audio src={src} />
                </Sequence>
              );
            }

            if (track.type === "text" && clip.text_content) {
              // 与同时间视觉 clip 的 lower_third 内容完全相同的文本 clip 是重复角标，
              // 交给视觉分支的 LowerThird 统一渲染，这里跳过。
              const dupeKey = `${Math.round((clip.start_time || 0) * 10)}::${clip.text_content.trim()}`;
              if (visualLowerThirdKeys.has(dupeKey)) {
                return null;
              }
              // 文本 clip 自身的 lower_third 若与同时间视觉 clip 的角标相同，
              // 视觉分支已经渲染过，这里不再叠第二次（实测 LLM 时间线会三处重复）。
              const ownLtKey = clip.style?.lower_third
                ? `${Math.round((clip.start_time || 0) * 10)}::${String(clip.style.lower_third).trim()}`
                : null;
              const skipOwnLowerThird = !!ownLtKey && visualLowerThirdKeys.has(ownLtKey);
              return (
                <Sequence
                  key={key}
                  from={startFrame}
                  durationInFrames={durationFrames}
                >
                  <MotionText
                    layoutStyle={buildTextStyle(clip, scale)}
                    duration={durationFrames}
                    text={clip.text_content}
                    transition={clip.style?.transition}
                    brandColor={brandColor}
                  />
                  {!skipOwnLowerThird && renderLowerThird(clip, durationFrames)}
                </Sequence>
              );
            }

            if (track.type === "overlay") {
              // overlay 文本与同时间视觉 clip 的 lower_third 相同时同样是重复角标，
              // 统一交给视觉分支的 LowerThird 渲染，避免同一文字叠三遍。
              if (clip.text_content) {
                const overlayDupeKey = `${Math.round((clip.start_time || 0) * 10)}::${clip.text_content.trim()}`;
                if (visualLowerThirdKeys.has(overlayDupeKey)) {
                  return null;
                }
              }
              return (
                <Sequence
                  key={key}
                  from={startFrame}
                  durationInFrames={durationFrames}
                >
                  <MotionOverlay
                    layoutStyle={buildOverlayStyle(clip, scale)}
                    duration={durationFrames}
                    transition={clip.style?.transition}
                  >
                    {clip.text_content && (
                      <span
                        style={{
                          color: clip.style?.color || "#fff",
                          fontSize:
                            (clip.style?.fontSize || 64) * scale,
                          fontFamily: FONT_STACK,
                          fontWeight: clip.style?.fontWeight || "bold",
                        }}
                      >
                        {clip.text_content}
                      </span>
                    )}
                  </MotionOverlay>
                </Sequence>
              );
            }

            return null;
          })
        )}

        {allClips.length === 0 && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontSize: 64,
              fontFamily: FONT_STACK,
              fontWeight: "bold",
              textShadow: "0 2px 20px rgba(0,0,0,0.5)",
            }}
          >
            ClipWorks
          </div>
        )}
      </div>

      {/* 品牌点缀：底部品牌色条 + 左上角品牌色小标，统一全片品牌识别。 */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: Math.max(10, Math.round(canvasHeight * 0.012)),
          background: brandColor,
          boxShadow: `0 0 24px ${brandColor}`,
          zIndex: 9999,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: Math.round(canvasWidth * 0.04),
          top: Math.round(canvasHeight * 0.04),
          width: Math.round(canvasWidth * 0.10),
          height: Math.max(8, Math.round(canvasHeight * 0.008)),
          borderRadius: 999,
          background: brandColor,
          opacity: 0.92,
          zIndex: 9999,
        }}
      />
    </AbsoluteFill>
  );
};
