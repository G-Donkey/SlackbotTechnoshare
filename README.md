# TechnoShare Commentator (POC)

**A proactive AI agent for automated technical knowledge management.**

---

## 📖 Business Overview

### 🎯 Mission
In a fast-paced AI consulting environment, staying updated is critical. Team members constantly share valuable articles, papers, and tools in Slack channels like `#technoshare`. However, due to high volume and busy schedules, **90% of these links are lost in the noise** or never fully leveraged for client projects.

**TechnoShare Commentator** solves this by transforming passive "link dumps" into active, actionable intelligence. It ensures every shared resource is analyzed, summarized, and mapped to specific business opportunities.

### 💎 Value Proposition
1.  **Reduce Information Overload**: Instead of reading 10-page papers, consultants get a 10-sentence executive summary instantly.
2.  **Contextual Relevance**: The bot doesn't just summarize; it explicitly answers: *"How can we use this for our clients?"* and *"What are the risks?"*
3.  **Active Knowledge Base**: By processing links immediately, we build a searchable repository of vetted tools and insights, preventing knowledge silos.
4.  **Quality Control**: The prompt-chaining architecture ensures high-fidelity extractions, filtering out clickbait and focusing on technical substance.

### ⚙️ How It Works
1.  **Listen**: The bot monitors specific Slack channels for links.
2.  **Read & Search**: It autonomously visits the URL. If the content is complex, it uses an **LLM-powered Search Tool** to navigate the page and extract key facts.
3.  **Analyze**: It runs a multi-stage reasoning process:
    *   *Stage A*: Extract objective facts and technical specs.
    *   *Stage B*: Synthesize insights, assess project relevance, and identify risks.
4.  **Engage**: It posts a threaded reply in Slack with a structured summary, enabling immediate team discussion.

---

## 🏗 Technical Architecture

This repository is built with **production-grade engineering practices**, moving beyond a simple script to a robust, scalable system.

### Core Principles
-   **Hexagonal Architecture**: Business logic is isolated from external systems (Slack, OpenAI). This allows us to swap specific components (e.g., changing the LLM provider) without rewriting the core bot.
-   **Agentic Capabilities**: The system isn't just a text-in/text-out pipeline. It has **Tools** (like Web Search) that it can decide to use dynamically when it encounters missing information.
-   **Observability**: Every interaction is logged with structured metadata (tokens used, tools called, sources cited), essential for debugging and cost management.

### The Codebase
-   **`src/technoshare_commentator`**: The application core.
    -   `pipeline/`: Orchestrates the Agent workflow (Ingest -> Analyze -> Reply).
    -   `llm/`: Handles AI logic, including **Prompt Chaining** and **Structured Outputs** (Pydantic objects) for reliability.
    -   `retrieval/`: Adapters for fetching content from generic web pages, GitHub, or ArXiv.
-   **`tests/`**: A comprehensive test suite featuring:
    -   **Unit Tests**: Fast, mocked tests for logic verification.
    -   **Integration Tests**: Real-world scenarios (e.g., "Actually read a Meta AI blog post") gated by environment flags to control costs.
    -   **Fixtures**: Modular setup for clean, readable test code.

---

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
   - Optionally configure MLflow (see [MLflow Setup](#mlflow-llmops-optional))

## Running

1. **MLflow Server** (optional, for tracking/observability):
   ```bash
   ./scripts/start_mlflow.sh
   ```
   Access UI at http://127.0.0.1:5000

2. **Ingest Server** (receives Slack events):
   ```bash
   uv run uvicorn technoshare_commentator.main_ingest:app --reload --port 3000
   ```
   *Note: Ensure your tunnel (ngrok) points to localhost:3000*

3. **Worker** (processes jobs):
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
- **Run evaluation suite**:
  ```bash
  python scripts/run_eval.py
  ```
- **Sync prompts to MLflow**:
  ```bash
  python scripts/sync_prompts.py
  ```

---

## 🔬 MLflow LLMOps (Optional)

This project includes comprehensive MLflow-based LLMOps for production-grade observability:

### Features
- **📊 Experiment Tracking**: Automatic logging of params, metrics, and artifacts for every job
- **🔍 LLM Tracing**: Span-based observability for LLM calls, tool usage, and pipeline stages
- **📝 Prompt Versioning**: Version control and aliasing for prompt templates
- **✅ Evaluation Suite**: Automated quality checks with hard and soft scorers

### Quick Start

```bash
# 1. Start MLflow server
./scripts/start_mlflow.sh

# 2. Add to .env
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MLFLOW_ENABLE_TRACKING=true
MLFLOW_ENABLE_TRACING=true

# 3. Run pipeline (auto-logs to MLflow)
python -m technoshare_commentator.main_worker

# 4. View UI
open http://127.0.0.1:5000
```

### Documentation
- **📖 Full Guide**: [docs/MLFLOW_GUIDE.md](docs/MLFLOW_GUIDE.md)
- **⚡ Quick Reference**: [docs/MLFLOW_QUICKSTART.md](docs/MLFLOW_QUICKSTART.md)

### What Gets Tracked
Every pipeline run automatically logs:
- Latency, token counts, tool usage
- Evidence, facts, outputs as artifacts
- Quality gate results
- Source URLs and adapter coverage
- Nested spans for debugging

### Evaluation
```bash
# Add test cases to data/eval_dataset.json
# Run evaluation suite
python scripts/run_eval.py

# View results in MLflow UI (experiment: technoshare_eval)
```

---
