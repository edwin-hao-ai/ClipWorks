import { Composition, CalculateMetadataFunction, registerRoot } from "remotion";
import { GenericComp } from "./compositions/GenericComp";

interface CompositionProps {
  composition: {
    duration?: number;
    tracks?: unknown[];
  };
}

const calculateMetadata: CalculateMetadataFunction<CompositionProps> = ({
  props,
}) => {
  const duration = props.composition?.duration ?? 30;
  return {
    durationInFrames: Math.max(1, Math.round(duration * 30)),
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
      defaultProps={{ composition: { duration: 30, tracks: [] } }}
      calculateMetadata={calculateMetadata}
    />
  );
};

registerRoot(RemotionRoot);
