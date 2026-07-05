import { Composition } from "remotion";
import { GenericComp } from "./compositions/GenericComp";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Generic"
      component={GenericComp}
      durationInFrames={900}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ composition: { duration: 30, tracks: [] } }}
    />
  );
};
