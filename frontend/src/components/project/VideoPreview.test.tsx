import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VideoPreview } from "./VideoPreview";

describe("VideoPreview", () => {
  it("renders video when output_url is present", () => {
    render(<VideoPreview outputUrl="/api/static/test.mp4" htmlOutputUrl="/api/static/test/index.html" />);
    expect(screen.getByText("成片预览")).toBeInTheDocument();
    const video = document.querySelector("video");
    expect(video).toBeInTheDocument();
    expect(video?.getAttribute("src")).toBe("/api/static/test.mp4");
  });

  it("falls back to html preview when no output_url", () => {
    render(<VideoPreview outputUrl={null} htmlOutputUrl="/api/static/test/index.html" />);
    expect(screen.getByText("HTML 预览")).toBeInTheDocument();
    const iframe = document.querySelector("iframe");
    expect(iframe).toBeInTheDocument();
  });
});
