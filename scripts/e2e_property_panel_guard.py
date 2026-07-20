#!/usr/bin/env python3
"""验证修复②：属性面板逐键输入不再触发 Agent 渲染；画幅未变不触发；画幅真变才触发一次。"""
import asyncio

from playwright.async_api import async_playwright

UID = "e277eea9-9257-45ee-8276-43aec4535316"
PID = "fc04330d-8cc1-4dce-98d5-f431eb38aae5"  # 富测试项目（ready 态，15 clips）
BASE = "http://localhost:3000"


async def main() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        await ctx.add_cookies([{"name": "session_user_id", "value": UID, "domain": "localhost", "path": "/"}])
        page = await ctx.new_page()
        agent_calls: list[str] = []
        page.on(
            "request",
            lambda req: agent_calls.append(req.url)
            if "/agent/chat" in req.url and req.method == "POST"
            else None,
        )

        await page.goto(f"{BASE}/projects/{PID}", wait_until="networkidle")
        # 等属性面板的标题输入框出现（ready 视图）
        title_input = page.locator("div:has(> div > label:text('标题')) input").first
        await title_input.wait_for(timeout=15000)

        # 1) 逐键输入标题 5 个字
        await title_input.click()
        await title_input.press_sequentially("测试标题X", delay=50)
        await page.wait_for_timeout(1500)
        after_typing = len(agent_calls)
        print(f"[1] agent/chat calls after typing title: {after_typing} (expect 0)")

        # 2) 点击当前画幅（未变化）
        current_format = await page.evaluate(
            """(() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const active = btns.find(b => /^(16:9|9:16|1:1)$/.test(b.textContent || '')
                    && b.className.includes('bg-brand-900'));
                return active ? active.textContent : null;
            })()"""
        )
        if current_format:
            await page.get_by_role("button", name=current_format, exact=True).click()
            await page.wait_for_timeout(1500)
        after_same = len(agent_calls)
        print(f"[2] agent/chat calls after clicking SAME format {current_format}: {after_same} (expect {after_typing})")

        # 3) 点击不同画幅（真变化）——应恰好触发 1 次
        target = "9:16" if current_format != "9:16" else "16:9"
        await page.get_by_role("button", name=target, exact=True).click()
        await page.wait_for_timeout(2500)
        after_change = len(agent_calls)
        print(f"[3] agent/chat calls after changing format to {target}: {after_change} (expect {after_same} + 1)")

        await browser.close()

        assert after_typing == 0, "逐键输入触发了 Agent 渲染"
        assert after_same == after_typing, "点击相同画幅触发了 Agent 渲染"
        assert after_change == after_same + 1, f"画幅真变化应触发恰好 1 次，实际 {after_change - after_same}"
        print("PASS: 逐键输入/相同画幅不触发渲染，画幅真变化恰好触发 1 次")


if __name__ == "__main__":
    asyncio.run(main())
