import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";

interface Clip {
  start_time: number;
  duration: number;
  text_content?: string;
  style?: Record<string, any>;
}

interface Track {
  type: string;
  clips: Clip[];
}

export const GenericComp: React.FC<{ composition: { duration: number; tracks: Track[] } }> = ({
  composition,
}) => {
  const frame = useCurrentFrame();
  const currentTime = frame / 30;
  const activeClip = composition.tracks
    .flatMap((t) => t.clips)
    .find((c) => currentTime >= c.start_time && currentTime < c.start_time + c.duration);

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f0f1a", justifyContent: "center", alignItems: "center" }}>
      <div style={{ color: "#fff", fontSize: 64, textAlign: "center" }}>
        {activeClip?.text_content || "ClipWorks"}
      </div>
    </AbsoluteFill>
  );
};
