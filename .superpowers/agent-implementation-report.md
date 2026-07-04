# ClipWorks Agent Implementation Report

## Status

**DONE_WITH_CONCERNS**

The real LLM-powered Agent pipeline is implemented end-to-end. Backend tests, frontend build, and frontend tests all pass. The Agent chat and agent-generate endpoints work locally and gracefully fall back to deterministic/mock output when the Kimi API is unavailable. Docker image build for the backend could not be fully verified in this environment because `apt-get` from the Debian repositories timed out; the frontend image builds successfully.

## Files Changed

### Backend

- `backend/requirements.txt` — added `beautifulsoup4`.
- `backend/Dockerfile` — added Node.js installation so `npx hyperframes` can run inside the backend container.
- `backend/app/main.py` — imports `app.config` to load `.env` at startup and includes the new `agent.router`.
- `backend/app/config.py` *(new)* — centralizes env vars (`KIMI_API_KEY`, `KIMI_BASE_URL`, `KIMI_MODEL`, `HYPERFRAMES_CMD`, `ASSETS_DIR`) and loads `backend/.env` via `python-dotenv`.
- `backend/app/agent/__init__.py` *(new)* — package exports.
- `backend/app/agent/llm.py` *(new)* — `KimiClient` wrapper around `openai.OpenAI` with `chat_completion` / `chat_completion_json` helpers.
- `backend/app/agent/prompts.py` *(new)* — system prompts for `PLAN_VIDEO`, `BUILD_COMPOSITION`, `GENERATE_HTML`, and `MODIFY_VIDEO`.
- `backend/app/agent/planner.py` *(new)* — `plan_video(source_url, user_prompt)` with deterministic fallback plan.
- `backend/app/agent/composer.py` *(new)* — `build_composition(video_plan)` with deterministic fallback composition generator.
- `backend/app/agent/html_generator.py` *(new)* — `generate_html(composition, assets)` with self-contained HyperFrames-style HTML fallback.
- `backend/app/agent/modifier.py` *(new)* — `modify_composition(composition, instruction)` with rule-based fallback modifications.
- `backend/app/services/__init__.py` *(new)* — services package marker.
- `backend/app/services/scraper.py` *(new)* — webpage title/description/image extraction via `httpx` + `BeautifulSoup`.
- `backend/app/services/assets.py` *(new)* — `resolve_image_asset`, `download_image`, and `persist_asset` helpers.
- `backend/app/routers/renders.py` — replaced `mock_render_task` with `render_video_task`, added `POST /projects/{id}/renders/agent-generate`, kept deterministic fallback when HyperFrames is unavailable.
- `backend/app/routers/agent.py` *(new)* — `POST /projects/{id}/agent/chat` endpoint that modifies the composition and optionally triggers a background re-render.

### Frontend

- `frontend/src/components/project/AgentChat.tsx` *(new)* — chat panel for agent instructions with quick prompts and status display.
- `frontend/src/components/project/GenerationPanel.tsx` — added optional generation prompt input; sends prompt to `agent-generate` when provided.
- `frontend/src/app/projects/[id]/page.tsx` — integrated `AgentChat` into the workspace sidebar.

## Test / Build Summary

- `cd backend && python -m pytest tests/test_api.py` — **15 passed**.
- `cd frontend && npm run build` — **succeeded**.
- `cd frontend && npm test` — **5 passed**.
- Local backend smoke test against the running Postgres container:
  - `POST /projects/{id}/agent/chat` with message `把标题改成红色` returned `200` and updated the text clip style color to `#ff3333`.
  - `POST /projects/{id}/renders/agent-generate` with prompt `more energetic` returned `202`, generated HTML at `/api/static/{project_id}/index.html`, and completed with fallback MP4 `/api/static/sample.mp4` because HyperFrames CLI is not installed locally.

## Concerns

1. **HyperFrames rendering in container could not be fully verified.** The local environment does not have the HyperFrames CLI installed, so the render step falls back to the sample MP4 after generating the HTML preview. The backend Dockerfile now installs Node.js, but I could not complete a `docker compose build backend` because Debian package downloads in this environment consistently timed out. Once the container builds in an environment with normal network access, `npx hyperframes render` should either work or fall back gracefully.

2. **Kimi API returned 401 during local testing.** The configured `KIMI_API_KEY` appears invalid in this environment, so all Agent LLM calls fell back to deterministic plans/compositions/HTML. This demonstrates the required fallback behavior, but the rich LLM-generated output will only be seen with a valid API key.

3. **Agent render time with invalid API key.** Each LLM call waits for the OpenAI client to fail (≈10s timeout) before falling back. With three agent stages (plan, compose, generate HTML) this can add ~30s to the first render. With a valid key this becomes real generation time instead.

4. **No new automated tests were added** for the Agent modules. The existing API tests continue to pass; additional unit tests for `agent/` and `services/` would be a good follow-up.
