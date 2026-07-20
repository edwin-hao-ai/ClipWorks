#!/usr/bin/env python3
"""最终复验：深色桌面 /projects 封面+分页按钮；浅色主题 Sidebar 选中态对比度。"""
import asyncio
import os

from playwright.async_api import async_playwright

UID = "e277eea9-9257-45ee-8276-43aec4535316"
OUT = "data/e2e_audit/taste_fix"
BASE = "http://localhost:3000"


async def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        # (a) 深色桌面 /projects：封面渲染 + 分页按钮
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        await ctx.add_cookies([{"name": "session_user_id", "value": UID, "domain": "localhost", "path": "/"}])
        page = await ctx.new_page()
        await page.goto(f"{BASE}/projects", wait_until="networkidle")
        await page.wait_for_function(
            "document.querySelectorAll('a[href^=\"/projects/\"]').length > 0", timeout=15000
        )
        await page.wait_for_timeout(3000)  # 等封面图加载
        covers = await page.evaluate(
            """Array.from(document.querySelectorAll('a[href^="/projects/"] img'))
               .filter(img => img.complete && img.naturalWidth > 0).length"""
        )
        load_more = await page.locator("text=/加载更多/").count()
        theme = await page.evaluate("document.documentElement.getAttribute('data-theme')")
        print(f"[a] theme={theme} covers_loaded={covers} load_more_buttons={load_more}")
        await page.screenshot(path=f"{OUT}/final_projects_dark.png", full_page=False)
        await ctx.close()

        # (b) 浅色主题：Sidebar 选中态对比度（nav-active -> brand-700）
        ctx2 = await browser.new_context(viewport={"width": 1440, "height": 900})
        await ctx2.add_cookies([{"name": "session_user_id", "value": UID, "domain": "localhost", "path": "/"}])
        page2 = await ctx2.new_page()
        await page2.goto(f"{BASE}/projects", wait_until="domcontentloaded")
        await page2.evaluate("localStorage.setItem('cw_theme', 'light')")
        await page2.reload(wait_until="networkidle")
        await page2.wait_for_timeout(1500)
        theme2 = await page2.evaluate("document.documentElement.getAttribute('data-theme')")
        # 取当前路由对应的导航项 computed color
        nav_color = await page2.evaluate(
            """(() => {
                const link = document.querySelector('nav a[aria-current="page"]')
                    || document.querySelector('aside a[aria-current="page"]');
                if (!link) return null;
                return getComputedStyle(link).color;
            })()"""
        )
        print(f"[b] theme={theme2} active_nav_color={nav_color}")
        await page2.screenshot(path=f"{OUT}/final_projects_light.png", full_page=False)
        await ctx2.close()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
