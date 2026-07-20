import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { VideoPreview } from "./VideoPreview";

const SAMPLE_HTML =
  '<!DOCTYPE html><html><head></head><body><div id="stage"><div class="scene scene-0">hi</div></div></body></html>';

describe("VideoPreview", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        text: () => Promise.resolve(SAMPLE_HTML),
      })
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders video when output_url is present", () => {
    render(<VideoPreview outputUrl="/api/static/test.mp4" htmlOutputUrl="/api/static/test/index.html" />);
    expect(screen.getByText("成片预览")).toBeInTheDocument();
    const video = document.querySelector("video");
    expect(video).toBeInTheDocument();
    expect(video?.getAttribute("src")).toBe("/api/static/test.mp4");
  });

  it("falls back to html preview when no output_url", async () => {
    render(<VideoPreview outputUrl={null} htmlOutputUrl="/api/static/test/index.html" />);
    expect(screen.getByText("HTML 预览")).toBeInTheDocument();
    const iframe = await waitFor(() => {
      const el = document.querySelector("iframe");
      if (!el) throw new Error("iframe not ready");
      return el;
    });
    // Preview injects a patch that keeps animations looping and forces scenes
    // visible; the original scene markup is preserved.
    expect(iframe.getAttribute("srcdoc")).toContain("__replay");
    expect(iframe.getAttribute("srcdoc")).toContain("scene-0");
  });
});
