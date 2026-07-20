import { Composition, CalculateMetadataFunction, registerRoot } from "remotion";
import { GenericComp } from "./compositions/GenericComp";
import type { Track } from "./compositions/GenericComp";

type CompositionProps = {
  composition: {
    width?: number;
    height?: number;
    duration?: number;
    tracks?: Track[];
    metadata?: { brand_color?: string; brand_font?: string; engine?: string };
  };
  assets?: Record<string, string>;
};

const calculateMetadata: CalculateMetadataFunction<CompositionProps> = ({
  props,
}) => {
  const composition = props.composition || {};
  const duration = composition.duration ?? 30;
  return {
    durationInFrames: Math.max(1, Math.round(duration * 30)),
    width: composition.width ?? 1920,
    height: composition.height ?? 1080,
    props,
  };
};

const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Generic"
      component={GenericComp}
      durationInFrames={900}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ composition: { duration: 30, tracks: [] }, assets: {} }}
      calculateMetadata={calculateMetadata}
    />
  );
};

registerRoot(RemotionRoot);
