"""Browser E2E check for the agentic planning UI.

Requires the local stack to be running (docker compose up -d) and Playwright
with Chromium installed.

This script seeds a project with a pending plan directly in the database, then
uses Playwright to verify that the workspace shows the plan card and the
approve/reject buttons.

Usage:
  cd backend && source .venv/bin/activate && cd .. && python scripts/e2e_agentic_ui.py
"""
import json
import os
import sys
import time

import requests
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load backend .env so we can connect to the same database the backend uses.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

BASE_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"
# Docker Compose exposes Postgres on localhost:5432, but backend/.env uses the
# internal service hostname. Rewrite it for scripts running outside Docker.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://clipworks:clipworks@localhost:5432/clipworks"
).replace("@postgres:", "@localhost:")

DEMO_PLAN = {
    "final_plan": True,
    "title": "便携式咖啡杯 · 随时温热",
    "hook": "通勤路上咖啡冷掉？轻巧保温杯让热饮随身随行",
    "format": "9:16",
    "duration": 30,
    "scenes": [
        {"start": 0, "duration": 5, "description": "开场痛点：通勤场景中热咖啡迅速变凉", "visual": "地铁女孩", "text": "通勤路上的咖啡总是冷掉？"},
        {"start": 5, "duration": 5, "description": "产品亮相：便携咖啡杯旋转登场", "visual": "产品渲染", "text": "XX 便携咖啡杯 · 随时温热"},
        {"start": 10, "duration": 5, "description": "突出便携：多场景轻松放入", "visual": "分屏动画", "text": "轻巧随行，一手掌握"},
        {"start": 15, "duration": 5, "description": "突出保温：长时间锁温效果", "visual": "温度计", "text": "12小时保温，热饮如初"},
        {"start": 20, "duration": 5, "description": "生活方式：小红书女孩的精致日常", "visual": "生活场景", "text": "小红书女孩の精致日常"},
        {"start": 25, "duration": 5, "description": "结尾行动号召：品牌信息+购买引导", "visual": "产品居中", "text": "立即入手，温暖随身"},
    ],
    "assets_needed": ["产品高清渲染图", "品牌 logo", "背景音乐"],
    "engine_hint": "hyperframes",
}


def seed_project_state(project_id: str, user_id: str, status: str, pending_plan: dict | None = None):
    engine = create_engine(DATABASE_URL)
    messages = [
        {"role": "user", "content": "帮我做一个便携式咖啡杯的产品介绍视频"},
        {"role": "assistant", "content": "好的，请告诉我时长和画幅。"},
        {"role": "user", "content": "30 秒，9:16"},
    ]
    if pending_plan:
        messages.append({"role": "assistant", "content": json.dumps(pending_plan, ensure_ascii=False)})
    agent_state = {
        "messages": messages,
        "pending_plan": pending_plan,
        "step": "pending_approval" if pending_plan else "chatting",
    }
    with engine.connect() as conn:
        conn.execute(
            text(
                "UPDATE projects SET status = :status, agent_state = :state WHERE id = :id AND user_id = :user_id"
            ),
            {"status": status, "state": json.dumps(agent_state, ensure_ascii=False), "id": project_id, "user_id": user_id},
        )
        conn.commit()


def main():
    # 1. Mock login via API to create a session cookie.
    session = requests.Session()
    r = session.post(f"{API_URL}/auth/mock-login?provider=google")
    r.raise_for_status()
    user = r.json()["user"]
    user_id = user["id"]
    print(f"Logged in as {user['email']} ({user_id})")

    # 2. Create a project.
    r = session.post(
        f"{API_URL}/projects/",
        json={"title": "UI Planning Test", "source_url": "", "source_type": "url"},
    )
    r.raise_for_status()
    project_id = r.json()["id"]
    print(f"Created project {project_id}")

    # 3. Seed a pending plan in the database.
    seed_project_state(project_id, user_id, "planning", pending_plan=DEMO_PLAN)
    print("Seeded pending plan")

    # 4. Open the workspace in a browser and verify the plan card.
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context(viewport={"width": 1440, "height": 900})

        # Transfer the session cookie from requests to Playwright.
        cookies = session.cookies.get_dict()
        for name, value in cookies.items():
            context.add_cookies(
                [
                    {
                        "name": name,
                        "value": value,
                        "domain": "localhost",
                        "path": "/",
                    }
                ]
            )

        page = context.new_page()
        page.goto(f"{BASE_URL}/projects/{project_id}")
        print("Opened project page:", page.url)

        # Wait for the plan card.
        try:
            page.wait_for_selector("text=方案已就绪", timeout=10000)
        except Exception as exc:
            page.screenshot(path="/tmp/e2e_agentic_ui_fail.png", full_page=True)
            print("FAIL: plan card not visible")
            print(exc)
            browser.close()
            sys.exit(1)

        page.screenshot(path="/tmp/e2e_agentic_ui_plan.png", full_page=True)
        print("PASS: plan card is visible")

        # Verify plan details are rendered.
        assert page.is_visible(f"text={DEMO_PLAN['title']}")
        assert page.is_visible(f"text={DEMO_PLAN['scenes'][0]['description']}")
        print("PASS: plan title and scene descriptions rendered")

        # Verify the generating state is rendered after we flip the status in the DB.
        seed_project_state(project_id, user_id, "generating", pending_plan=None)
        page.reload()
        page.wait_for_selector("text=生成中", timeout=10000)
        page.screenshot(path="/tmp/e2e_agentic_ui_generating.png", full_page=True)
        print("PASS: generating state is visible")

        # Seed a second project to verify the reject UI path.
        r2 = session.post(
            f"{API_URL}/projects/",
            json={"title": "UI Reject Test", "source_url": "", "source_type": "url"},
        )
        r2.raise_for_status()
        reject_project_id = r2.json()["id"]
        seed_project_state(reject_project_id, user_id, "planning", pending_plan=DEMO_PLAN)
        page.goto(f"{BASE_URL}/projects/{reject_project_id}")
        page.wait_for_selector("text=方案已就绪", timeout=10000)
        page.click("text=再改改")
        page.wait_for_selector("text=告诉我哪里需要调整", timeout=5000)
        page.screenshot(path="/tmp/e2e_agentic_ui_reject.png", full_page=True)
        print("PASS: reject mode is visible")

        browser.close()


if __name__ == "__main__":
    main()
