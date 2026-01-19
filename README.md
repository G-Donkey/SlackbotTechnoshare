# TechnoShare Commentator

**AI-powered Slack bot for automated technical knowledge management.**

---

## 📖 Overview

TechnoShare Commentator monitors Slack channels for shared links, analyzes them using a two-stage LLM pipeline, and posts structured summaries as threaded replies.

### Key Features
- **🔌 Socket Mode**: WebSocket-based connection (no public URL required)
- **🧠 Two-Stage LLM Pipeline**: Fact extraction → Reply composition
- **📊 MLflow Integration**: Optional tracking and tracing for observability
- **⚡ Async Job Queue**: SQLite-backed queue with idempotent processing

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TechnoShare Commentator                   │
├─────────────────────────────────────────────────────────────┤
│  main_socket.py          │  main_worker.py                  │
│  (Socket Mode Listener)  │  (Job Processor)                 │
│          │               │          │                       │
│          ▼               │          ▼                       │
│  ┌───────────────┐       │  ┌───────────────────────────┐  │
│  │ Slack Events  │       │  │    7-Stage Pipeline       │  │
│  │ (via WebSocket)│       │  │  1. URL extraction       │  │
│  └───────┬───────┘       │  │  2. Content retrieval    │  │
│          │               │  │  3. Stage A (facts)      │  │
│          ▼               │  │  4. Stage B (composition)│  │
│  ┌───────────────┐       │  │  5. Quality gates        │  │
│  │ SQLite Queue  │◄──────┼──│  6. Slack posting        │  │
│  │ (jobs table)  │       │  │  7. Job completion       │  │
│  └───────────────┘       │  └───────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure
```
src/technoshare_commentator/
├── main_socket.py      # Socket Mode listener (slack-bolt)
├── main_worker.py      # Job processing worker
├── config.py           # Pydantic settings
├── llm/               # LLM logic (Stage A, Stage B, client)
├── pipeline/          # Pipeline orchestration
├── retrieval/         # URL fetching and content extraction
├── quality/           # Output validation gates
├── rendering/         # Slack mrkdwn formatting
├── schemas/           # Pydantic models
├── slack/             # Slack client and posting
├── store/             # SQLite database layer
└── mlops/             # MLflow tracking/tracing (optional)
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11+
- [uv](https://astral.sh/uv) package manager
- Slack App with Socket Mode enabled

### 2. Install
```bash
uv sync
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
OPENAI_API_KEY=sk-...
TECHNOSHARE_CHANNEL_ID=C...
```

### 4. Verify Configuration
```bash
uv run python scripts/test_socket_config.py
```

### 5. Run
```bash
# Terminal 1: Socket Mode listener
uv run python -m technoshare_commentator.main_socket

# Terminal 2: Job worker
uv run python -m technoshare_commentator.main_worker
```

---

## 🔬 MLflow (Optional)

Enable LLM observability with MLflow tracking and tracing.

### Setup
```bash
# Start MLflow server
./scripts/start_mlflow.sh

# Add to .env
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MLFLOW_ENABLE_TRACKING=true
MLFLOW_ENABLE_TRACING=true
```

### What Gets Tracked
- Pipeline latency and token usage
- Evidence, facts, and outputs as artifacts
- Quality gate results
- Nested spans for debugging

📖 See [docs/MLFLOW.md](docs/MLFLOW.md) for full documentation.

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=technoshare_commentator

# Run integration tests (requires API keys)
INTEGRATION_TEST=1 uv run pytest tests/integration/
```

---

## 📚 Documentation

- [Slack Integration](src/technoshare_commentator/slack/README.md) - Socket Mode architecture
- [MLflow Guide](docs/MLFLOW.md) - LLMOps and observability

---
