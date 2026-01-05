# TechnoShare Commentator POC

A local agent that monitors `#technoshare`, summarizes links, and explains their relevance to our projects.

## Setup

1. **Install uv**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. **Install dependencies**:
   ```bash
   uv sync
   ```
3. **Configure Environment**:
   - Copy `.env.example` to `.env`
   - Fill in Slack tokens and OpenAI key.
   - Set `TECHNOSHARE_CHANNEL_ID`.

## Running

1. **Ingest Server** (receives Slack events):
   ```bash
   uv run uvicorn technoshare_commentator.main_ingest:app --reload --port 3000
   ```
   *Note: Ensure your tunnel (ngrok) points to localhost:3000*

2. **Worker** (processes jobs):
   ```bash
   uv run python -m technoshare_commentator.main_worker
   ```

## Development

- **Run tests**:
  ```bash
  uv run pytest
  ```
- **Replay event**:
  ```bash
  uv run python scripts/replay_event.py
  ```
