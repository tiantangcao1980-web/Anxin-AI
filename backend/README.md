# Anxin AI Backend

FastAPI backend service for Anxin Smart Legal Services.

## Dev Commands

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8001
```
