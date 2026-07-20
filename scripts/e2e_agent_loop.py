"""Smoke test the four-step wizard API without a browser.

Note: mock auth is cookie-based. You must already be logged in (session_user_id
cookie set in the same requests Session, e.g. by hitting the local Next.js login
flow first) or have auth disabled in test mode for this script to work.
"""
import argparse
import os
import sys

import requests

API = os.getenv("CLIPWORKS_API", "http://localhost:8000")


def main():
    parser = argparse.ArgumentParser(description="Smoke test the agent loop wizard API.")
    parser.add_argument("--project-id", required=True, help="Project UUID")
    parser.add_argument(
        "--api",
        default=API,
        help="ClipWorks API base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    s = requests.Session()
    # Assumes mock auth cookie already set or auth is disabled in test mode.
    # For local dev, visit http://localhost:3000/login first to get the cookie.

    r = s.post(f"{args.api}/projects/{args.project_id}/agent/reset")
    print("reset", r.status_code, r.json())
    if r.status_code != 200:
        sys.exit(1)

    for step in ["script", "assets", "scenes", "effects"]:
        print(f"\n--- running {step} ---")
        r = s.post(
            f"{args.api}/projects/{args.project_id}/agent/step/{step}",
            json={"user_input": ""},
            stream=True,
        )
        if r.status_code != 200:
            print(f"{step} failed", r.status_code, r.text)
            sys.exit(1)
        for line in r.iter_lines():
            if line:
                print(line.decode())

    r = s.post(f"{args.api}/projects/{args.project_id}/agent/approve", json={})
    print("\napprove", r.status_code, r.json())
    if r.status_code != 200:
        sys.exit(1)


if __name__ == "__main__":
    main()
