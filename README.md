# research-agent

Multi-agent research assistant: FastAPI + LangChain agents on Groq, Tavily for
search, Supabase for state, LangSmith for tracing. See `architecture.excalidraw`
for the full design, build plan and reference snippets.

## Layout

`src/` is the source root — it is *not* a package. Modules under it
(`config`, `integrations`, `tools`) are imported as top-level names, with
`src/` placed on `sys.path` by `pythonpath` in `pyproject.toml` (tests) and
`--app-dir src` (uvicorn). There is deliberately no `[build-system]`: this is an
application, not a distributable library.

## Setup

```bash
uv sync                 # runtime deps
uv sync --group dev     # + pytest
cp .env.example .env    # then fill in the required keys
```

## Run

```bash
uvicorn main:app --app-dir src --reload
```

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | liveness — cheap, no external calls, safe to poll |
| `GET /health/deep` | readiness — checks Supabase + Groq + LangSmith, costs an LLM call |

## Test

```bash
pytest                  # unit tests; integration tests deselected
pytest -m integration   # hits live Supabase and Groq — needs real credentials
```
