#!/usr/bin/env python3
"""验证修复①：渲染完成后工作区无需手动刷新自动退出「生成中」视图，且轮询终止。

手法（镜像生产链路）：
1. API 建项目 -> DB 直接把项目置为 generating + 插入 running 任务（等价于 render_task 正在跑）。
2. 浏览器打开工作区 -> 确认 GenerationPanel 显示。
3. DB 把任务置为 completed、项目置为 ready（等价于 render_task 收尾落库）。
4. 断言：页面在不刷新的前提下切到成片视图（出现「用当前时间线重新渲染」「时间线编辑器」），
   且 /renders/ 轮询停止。
"""
import asyncio
import json
import subprocess
import time
import urllib.request

from playwright.async_api import async_playwright

UID = "e277eea9-9257-45ee-8276-43aec4535316"
BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = "data/e2e_audit/taste_fix/final_render_transition.png"


def psql(sql: str) -> str:
    r = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", "psql", "-U", "clipworks", "-d", "clipworks", "-tAc", sql],
        capture_output=True, text=True, cwd="/Users/edwinhao/ClipWorks",
    )
    if r.returncode != 0:
        raise RuntimeError(f"psql failed: {r.stderr}")
    return r.stdout.strip()


def api(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        method=method,
        headers={"Cookie": f"session_user_id={UID}", "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body is not None else None,
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())


async def main() -> None:
    project = api("POST", "/projects/", {"title": "E2E Transition Verify"})
    pid = project["id"]
    print(f"project={pid}")
    try:
        psql(f"UPDATE projects SET status='generating' WHERE id='{pid}';")
        psql(
            f"INSERT INTO render_jobs (id, project_id, status, progress, created_at) "
            f"VALUES (gen_random_uuid()::text, '{pid}', 'running', 50, now());"
        )

        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
            await ctx.add_cookies(
                [{"name": "session_user_id", "value": UID, "domain": "localhost", "path": "/"}]
            )
            page = await ctx.new_page()
            flip_time: list[float] = []

            list_polls: list[float] = []
            page.on(
                "request",
                # 只统计列表轮询端点，排除 SSE 长连接 /renders/stream
                lambda req: list_polls.append(time.time()) if req.url.endswith(f"/projects/{pid}/renders/") else None,
            )

            await page.goto(f"{BASE}/projects/{pid}", wait_until="networkidle")
            await page.get_by_text("生成", exact=False).first.wait_for(timeout=15000)
            gen_visible = await page.locator("text=/正在生成|生成队列/").first.is_visible()
            print(f"[1] generating panel visible: {gen_visible}")

            # 模拟 render_task 收尾：任务 completed + 项目 ready（生产里两者同时落库）
            psql(
                f"UPDATE render_jobs SET status='completed', progress=100, "
                f"output_url='/api/static/sample.mp4', completed_at=now() WHERE project_id='{pid}';"
            )
            psql(f"UPDATE projects SET status='ready' WHERE id='{pid}';")
            flip_time.append(time.time())
            polls_at_flip = len(list_polls)

            # 不刷新页面，等工作区自行切到成片视图
            await page.get_by_text("用当前时间线重新渲染").wait_for(timeout=15000)
            switch_time = time.time()
            editor_link = await page.locator("a[href$='/editor']").count()
            print(f"[2] switched to result view WITHOUT reload; editor links={editor_link}; "
                  f"switch_delay={switch_time - flip_time[0]:.1f}s")

            # 轮询应已终止：翻页瞬间可能赶上已在飞行/已排期的收尾轮询（有界，1-2s 内），
            # 关键断言是切换完成 3 秒之后不再有任何轮询。
            await page.wait_for_timeout(8000)
            extra = [t - flip_time[0] for t in list_polls[polls_at_flip:]]
            late_polls = [t for t in list_polls if t > switch_time + 3]
            print(f"[3] list polls after flip (rel seconds): {[f'{t:.1f}' for t in extra]}; "
                  f"polls later than switch+3s: {len(late_polls)}")

            await page.screenshot(path=OUT)
            await browser.close()

        assert gen_visible, "生成面板未显示"
        assert editor_link >= 1, "编辑器入口缺失"
        assert len(late_polls) == 0, f"轮询未终止: 切换 3s 后仍有 {len(late_polls)} 次请求"
        print("PASS: 渲染完成后工作区自动退出「生成中」、编辑器入口可见、轮询终止")
    finally:
        api("DELETE", f"/projects/{pid}")
        print("cleanup: test project deleted")


if __name__ == "__main__":
    asyncio.run(main())
