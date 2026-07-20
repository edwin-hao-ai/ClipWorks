"""Verify the NewProjectDialog 'upload' source actually uploads a file.

The upload tab used to be a stub ('上传功能在素材库中使用'). Now it must create
the project with source_type='upload' AND persist the file as a project asset.

Run: .e2e-venv/bin/python scripts/e2e_new_project_upload.py
"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
SAMPLE = OUT / "upload_sample.mp4"


def main():
    ok = True
    OUT.mkdir(parents=True, exist_ok=True)
    SAMPLE.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 64)

    created_pid = None
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(20000)

        page.goto(f"{BASE}/projects", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass

        page.get_by_role("button", name="新建项目").first.click()
        page.get_by_test_id("source-upload").wait_for(state="visible", timeout=8000)
        page.get_by_test_id("source-upload").click()

        # without a file, the create button is disabled
        submit_disabled_before = page.get_by_test_id("new-project-submit").is_disabled()
        print("SUBMIT_GATED_WITHOUT_FILE", "PASS" if submit_disabled_before else "FAIL")
        ok = ok and submit_disabled_before

        page.get_by_placeholder("例如：产品发布视频").fill("e2e-upload-proj")
        page.get_by_test_id("new-project-file").set_input_files(str(SAMPLE))
        page.wait_for_timeout(300)

        submit_enabled = page.get_by_test_id("new-project-submit").is_enabled()
        print("SUBMIT_ENABLED_WITH_FILE", "PASS" if submit_enabled else "FAIL")
        ok = ok and submit_enabled

        page.get_by_test_id("new-project-submit").click()
        try:
            page.wait_for_url(re.compile(r".*/projects/[0-9a-fA-F-]+"), timeout=15000)
        except Exception:
            page.screenshot(path=str(OUT / "new_project_upload_fail.png"), full_page=True)
            print("NAVIGATE", "FAIL", "did not land on workspace")
            b.close(); print("OVERALL FAIL"); sys.exit(1)

        m = re.search(r"/projects/([0-9a-fA-F-]+)", page.url)
        created_pid = m.group(1)

        proj = ctx.request.get(f"{API}/projects/{created_pid}").json()
        type_ok = proj.get("source_type") == "upload"
        print("PROJECT_SOURCE_TYPE", "PASS" if type_ok else "FAIL", f"source_type={proj.get('source_type')}")
        ok = ok and type_ok

        assets = ctx.request.get(f"{API}/projects/{created_pid}/assets/").json()
        vid = [a for a in assets if a.get("type") == "video" and a.get("source") == "upload"]
        asset_ok = len(vid) == 1 and vid[0].get("original_url") == "upload_sample.mp4"
        print("ASSET_UPLOADED", "PASS" if asset_ok else "FAIL",
              f"assets={[(a.get('type'), a.get('source'), a.get('original_url')) for a in assets]}")
        ok = ok and asset_ok

        page.screenshot(path=str(OUT / "new_project_upload.png"), full_page=True)
        b.close()

    if created_pid:
        try:
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True)
                ctx = b.new_context()
                ctx.request.post(f"{API}/auth/mock-login?provider=google")
                ctx.request.delete(f"{API}/projects/{created_pid}")
                b.close()
        except Exception: pass

    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
