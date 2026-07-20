"""End-to-end API check for the new agentic planning flow.

Requires the local stack to be running (docker compose up -d) and a valid
KIMI_API_KEY configured in backend/.env.

This script:
  1. Logs in via the mock auth endpoint.
  2. Creates a project.
  3. Starts a planning conversation.
  4. Continues the conversation until a plan is produced.
  5. Approves the plan and verifies the project moves to "generating".

Usage:
  cd backend && source .venv/bin/activate && cd .. && python scripts/e2e_agentic_planning.py
"""
import json
import sys
import time

import requests

BASE_URL = "http://localhost:8000"


def sse_post(session: requests.Session, path: str, payload: dict, timeout: float = 120.0):
    """POST and parse the SSE stream returned by the agent endpoints."""
    with session.post(
        f"{BASE_URL}{path}",
        json=payload,
        stream=True,
        timeout=timeout,
    ) as resp:
        resp.raise_for_status()
        tokens = []
        plan = None
        buffer = ""
        for chunk in resp.iter_content(chunk_size=1024):
            if not chunk:
                continue
            buffer += chunk.decode("utf-8")
            while "\n\n" in buffer:
                block, buffer = buffer.split("\n\n", 1)
                for line in block.splitlines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return {"tokens": tokens, "plan": plan}
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "token":
                        tokens.append(event.get("text", ""))
                    elif event.get("type") == "plan":
                        plan = event.get("plan")
                    elif event.get("type") == "done":
                        return {"tokens": tokens, "plan": plan}
        return {"tokens": tokens, "plan": plan}


def main():
    session = requests.Session()

    # 1. Mock login.
    r = session.post(f"{BASE_URL}/auth/mock-login?provider=google")
    r.raise_for_status()
    user = r.json()["user"]
    print(f"Logged in as {user['email']}")

    # 2. Create a project.
    r = session.post(
        f"{BASE_URL}/projects/",
        json={"title": "E2E planning test", "source_url": "", "source_type": "url"},
    )
    r.raise_for_status()
    project = r.json()
    project_id = project["id"]
    print(f"Created project {project_id}")

    # 3. Start planning with a prompt that includes the core details the agent needs.
    prompt = "帮我做一个便携式咖啡杯的产品介绍视频，30 秒，9:16，面向小红书年轻女性，风格活泼，突出保温和便携"
    print(f"\n[User] {prompt}")
    result = sse_post(session, f"/projects/{project_id}/agent/chat/stream", {"message": prompt})
    reply = "".join(result["tokens"])
    print(f"[Agent] {reply}")

    if result["plan"]:
        print("Agent produced a plan immediately (enough detail inferred).")
    else:
        # 4. Agent asked a question; answer generically so the test can proceed.
        answer = "产品是一款不锈钢保温杯，核心卖点是 12 小时保温和单手开合，适合通勤族"
        print(f"\n[User] {answer}")
        result = sse_post(session, f"/projects/{project_id}/agent/chat/stream", {"message": answer})
        reply = "".join(result["tokens"])
        print(f"[Agent] {reply}")

    if not result["plan"]:
        print("FAIL: Agent did not produce a plan after clarification.")
        sys.exit(1)

    plan = result["plan"]
    print(f"\nPlan received: {plan['title']} ({plan['format']}, {plan['duration']}s, {plan['engine_hint']})")

    # 5. Approve the plan.
    r = session.post(f"{BASE_URL}/projects/{project_id}/agent/approve", json={})
    r.raise_for_status()
    job = r.json()
    print(f"Approve returned job {job['job_id']}")

    # 6. Poll until project status moves to generating.
    for i in range(10):
        r = session.get(f"{BASE_URL}/projects/{project_id}")
        r.raise_for_status()
        status = r.json()["status"]
        print(f"Project status: {status}")
        if status == "generating":
            print("PASS: planning -> approve -> generating flow works")
            return
        time.sleep(1)

    print("FAIL: project did not move to generating after approve")
    sys.exit(1)


if __name__ == "__main__":
    main()
