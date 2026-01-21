# TechnoShare Commentator

**AI-powered Slack bot for automated technical knowledge management.**

---

## 📖 Overview

TechnoShare Commentator monitors Slack channels for shared links, analyzes them using a single-stage LLM pipeline, and posts structured summaries as threaded replies.

### Key Features
- **🔌 Socket Mode**: WebSocket-based connection (no public URL required)
- **🧠 Single-Stage LLM Pipeline**: Combined analysis and composition in one call
- **📊 Langfuse Integration**: Automatic LLM observability with OpenAI call tracing
- **⚡ Job Queue**: SQLite-backed queue with idempotent processing (may migrate to in-memory queue)
- **🔬 Evidence-Based**: Manual content extraction proven faster, cheaper, and more accurate than web search

> **Note**: Architecture is currently being evaluated and refined. The two-process design (listener + worker) may consolidate into a single process in future iterations.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TechnoShare Commentator                  │
├─────────────────────────────────────────────────────────────┤
│  main_socket.py          │  main_worker.py                  │
│  (Socket Mode Listener)  │  (Job Processor)                 │
│          │               │          │                       │
│          ▼               │          ▼                       │
│  ┌───────────────┐       │  ┌───────────────────────────┐   │
│  │ Slack Events  │       │  │    5-Stage Pipeline       │   │
│  │ (WebSocket).  │       │  │  1. URL extraction        │   │
│  └───────┬───────┘       │  │  2. Content retrieval     │   │
│          │               │  │  3. Analysis (LLM)        │   │
│          ▼               │  │  4. Quality gates         │   │
│  ┌───────────────┐       │  │  5. Slack posting         │   │
│  │ SQLite Queue  │◄──────┼──└───────────────────────────┘   │
│  │ (jobs table)  │       │            ▼                     │
│  └───────────────┘       │     ┌──────────────┐             │
│                          │     │  Langfuse    │             │
│                          │     │  (Optional)  │             │
│                          │     └──────────────┘             │
└─────────────────────────────────────────────────────────────┘

*Architecture under evaluation - may consolidate into single process*
*SQLite queue may migrate to in-memory queue for simplicity*
```

### Pipeline Stages Explained

#### Stage 1: URL Extraction
**Component:** `retrieval/url.py`

Parses incoming Slack messages to identify and extract URLs for processing.

**What it does:**
- Uses regex to find all URLs in message text
- Filters out Slack-internal links (e.g., `slack.com`, `files.slack.com`)
- Normalizes URLs (removes tracking parameters, ensures proper scheme)
- Returns list of unique URLs to process

**Example:**
```
Input message: "Check out this new AI paper https://arxiv.org/abs/2401.12345 
               and the GitHub repo https://github.com/openai/whisper"

Extracted URLs:
  - https://arxiv.org/abs/2401.12345
  - https://github.com/openai/whisper
```

---

#### Stage 2: Content Retrieval
**Component:** `retrieval/adapters/`, `retrieval/fetch.py`, `retrieval/extract.py`

Fetches web content and extracts clean, readable text for LLM analysis.

**What it does:**
1. **HTTP Fetch** (`fetch.py`): Makes GET request with custom User-Agent, follows redirects, retries 3x on failure
2. **Content Extraction** (`extract.py`): Uses `trafilatura` library to strip HTML boilerplate (ads, nav, footers)
3. **Snippet Creation**: Splits text into chunks (max 12 snippets, 500 chars each) with source attribution

**Example:**
```
Input URL: https://openai.com/blog/gpt-4o

Fetched HTML: <!DOCTYPE html><html>...(50KB of HTML)...</html>

Extracted Text (trafilatura):
  "GPT-4o is our newest flagship model that provides GPT-4-level 
   intelligence but is much faster and improves on its capabilities 
   across text, voice, and vision..."

Evidence Pack Output:
{
  "sources": [{"url": "https://openai.com/blog/gpt-4o", "title": "GPT-4o"}],
  "snippets": [
    {"id": 1, "content": "GPT-4o is our newest flagship model...", "source_url": "..."},
    {"id": 2, "content": "The model accepts any combination of text...", "source_url": "..."},
    ...
  ],
  "coverage": "full"
}
```

---

#### Stage 3: Analysis (Single LLM Call)
**Component:** `llm/analyze.py`, `llm/schema.py`

Single LLM call that analyzes evidence and generates structured Slack reply.

**What it does:**
1. Loads prompt template from `data/prompts/analyze.yaml`
2. Calls GPT-4o to generate all reply sections in one request
3. Enforces strict Pydantic validation on output structure
4. Automatically traced by Langfuse via `langfuse.openai` wrapper

**Output Schema:**
```python
class AnalysisResult(BaseModel):
    tldr: List[str]        # Exactly 3 full sentences
    summary: List[str]     # 10-15 full sentences
    projects: List[str]    # 3-8 bullet points
    similar_tech: List[str] # 0-8 bullet points
```

**Example Output:**
```json
{
  "tldr": [
    "GPT-4o is OpenAI's multimodal model combining text, audio, and vision capabilities.",
    "It offers significantly lower latency (232ms) making it suitable for real-time applications.",
    "API pricing at $5/1M tokens makes it cost-effective for production deployments."
  ],
  "summary": [
    "OpenAI released GPT-4o as their flagship multimodal model.",
    "The model processes text, images, and audio natively without separate pipelines.",
    "Average response latency of 232ms enables conversational voice applications.",
    "..."
  ],
  "projects": [
    "**Voice-enabled customer service**: Build real-time voice bots for call centers",
    "**Document analysis pipeline**: Process invoices with mixed text and images",
    "**Accessibility tools**: Create audio descriptions of visual content"
  ],
  "similar_tech": [
    "**Google Gemini**: Competing multimodal model with similar capabilities",
    "**Anthropic Claude 3**: Strong text performance but limited multimodal"
  ]
}
```

---

#### Stage 4: Quality Gates
**Component:** `quality/gates.py`

Validates analysis output before posting to ensure quality standards.

**What it does:**
1. **Sentence validation**: Each TL;DR and summary item must end with `.` `!` or `?`
2. **Length constraints**: TL;DR = exactly 3, Summary = 10-15, Projects = 3-8
3. **No newlines**: Individual items cannot contain line breaks
4. **Content checks**: Ensures no empty strings or placeholder text

**Validation Rules:**
```python
# Example validation from gates.py
def is_full_sentence(s: str) -> bool:
    s = s.strip()
    if not s:
        return False
    return any(char in {".", "!", "?"} for char in s[-3:])

# Fails validation:
"GPT-4o is a new model"  # Missing punctuation

# Passes validation:
"GPT-4o is a new model."  # Ends with period
```

**On Failure:**
- Job is marked as `failed` with error details
- No message posted to Slack
- Error logged for debugging

---

#### Stage 5: Slack Posting
**Component:** `slack/post_blocks.py`, `rendering/slack_format.py`

Converts analysis result to Slack Block Kit and posts as threaded reply.

**What it does:**
1. **Format conversion**: Transforms Markdown `**bold**` to Slack mrkdwn `*bold*`
2. **Block construction**: Builds Slack Block Kit JSON structure
3. **Thread reply**: Posts as reply to original message (using `thread_ts`)
4. **Error handling**: Retries on rate limits, logs failures

**Markdown → Slack mrkdwn:**
```
Input:  "**GPT-4o** is OpenAI's newest model"
Output: "*GPT-4o* is OpenAI's newest model"
```

**Slack Block Kit Output:**
```json
{
  "channel": "C0123456789",
  "thread_ts": "1705123456.789000",
  "blocks": [
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "*🤖 TL;DR*"}
    },
    {
      "type": "section", 
      "text": {"type": "mrkdwn", "text": "• GPT-4o is OpenAI's multimodal model..."}
    },
    {
      "type": "divider"
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "*📝 Summary*"}
    },
    ...
  ]
}
```

**Posted Result in Slack:**
```
┌────────────────────────────────────────────┐
│ 🤖 TL;DR                                   │
│ • GPT-4o is OpenAI's multimodal model...   │
│ • It offers significantly lower latency... │
│ • API pricing at $5/1M tokens...           │
│ ────────────────────────────────────────── │
│ 📝 Summary                                 │
│ OpenAI released GPT-4o as their flagship...│
│ ...                                        │
│ ────────────────────────────────────────── │
│ 💡 Project Ideas                           │
│ • *Voice-enabled customer service*: ...    │
│ • *Document analysis pipeline*: ...        │
└────────────────────────────────────────────┘
```

---

#### Stage 7: Job Completion
**Component:** `store/repo.py`, `store/db.py`

Finalizes the job in the database to prevent reprocessing.

**What it does:**
1. Updates job status from `processing` → `done`
2. Stores final output JSON as artifact
3. Records completion timestamp
4. Enables idempotency (same message won't be processed twice)

**Database Schema:**
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,           -- Unique job ID
    channel_id TEXT,               -- Slack channel
    thread_ts TEXT,                -- Thread timestamp
    message_ts TEXT,               -- Message timestamp  
    url TEXT,                      -- URL being processed
    status TEXT,                   -- pending/processing/done/failed
    output TEXT,                   -- JSON result (Stage B)
    error TEXT,                    -- Error message if failed
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Job Lifecycle:**
```
Message received → Job created (status: pending)
                 → Worker picks up (status: processing)
                 → Pipeline completes (status: done)
                 
If error:        → Pipeline fails (status: failed, error: "...")
```

**Idempotency Check:**
```python
# Before creating job, check if URL+channel+thread already processed
existing = repo.get_job_by_url_and_thread(url, channel_id, thread_ts)
if existing:
    logger.info(f"Job already exists: {existing.id}")
    return  # Skip duplicate
```

### Two-Process Architecture

The system currently runs as **two separate processes**:

**Socket Listener (`main_socket.py`)**
- Maintains persistent WebSocket connection to Slack
- Receives events in real-time via Socket Mode
- Quickly validates and queues messages (non-blocking)
- Handles Slack's acknowledgment requirements

**Job Worker (`main_worker.py`)**
- Polls SQLite queue for pending jobs
- Processes one job at a time (sequential)
- Handles LLM calls, retries, and error recovery
- Can be restarted without losing queued work

> **Architecture Status**: This two-process design with SQLite queue is being evaluated. Future iterations may:
> - Consolidate into single process for simplicity
> - Replace SQLite with in-memory queue
> - Current design prioritizes reliability and observability during initial development

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
└── mlops/             # Langfuse tracking/tracing (optional)
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
uv run python scripts/verify_config.py
```

### 5. Run
```bash
# Terminal 1: Socket Mode listener
uv run python -m technoshare_commentator.main_socket

# Terminal 2: Job worker
uv run python -m technoshare_commentator.main_worker
```

---

## 🔬 Langfuse Integration

Optional LLM observability platform for monitoring and debugging AI behavior.

### Why Langfuse?

- **Automatic OpenAI Tracing**: Zero-code instrumentation via `langfuse.openai` wrapper
- **Prompt Management**: Version control for prompts with A/B testing support
- **Cost Tracking**: Real-time token usage and cost analytics per trace
- **Debugging**: Inspect full prompt/completion pairs with metadata
- **Evaluation**: Score generations with custom metrics and judge LLMs

### Setup

**Option 1: Langfuse Cloud** (Recommended)
```bash
# Sign up at https://cloud.langfuse.com
# Add to .env:
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_ENABLED=true
```

**Option 2: Self-Hosted**
```bash
# Run Langfuse locally with Docker
docker run -p 3000:3000 \
  -e DATABASE_URL=postgresql://... \
  langfuse/langfuse:latest

# Add to .env:
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_ENABLED=true
```

### What Gets Traced

**Automatic OpenAI Tracing**:
- Every `run_analysis()` call creates a Langfuse trace
- Captures: model, prompt, completion, tokens (input/output), latency, cost
- Links traces to Slack message context (channel, thread, URL)

**Example Trace Data**:
```json
{
  "name": "run_analysis",
  "input": {
    "evidence": {"snippets": [...], "sources": [...]}
  },
  "output": {
    "tldr": [...],
    "summary": [...],
    "projects": [...]
  },
  "metadata": {
    "model": "gpt-4o",
    "tokens_input": 1523,
    "tokens_output": 892,
    "cost_usd": 0.0119,
    "latency_ms": 3421
  }
}
```

### Dashboard Features

- **Traces View**: Timeline of all LLM calls with filters (date, cost, latency)
- **Prompt Hub**: Manage prompt templates with versioning and rollback
- **Analytics**: Cost trends, token usage, P95 latency, error rates
- **Evaluations**: Score generations manually or with LLM-as-judge

### Disabling Tracing

Set `LANGFUSE_ENABLED=false` in `.env` to disable all tracing. The bot will function normally without any observability overhead.

---

## 🧪 Testing

### Test Organization

```
tests/
├── conftest.py              # Pytest fixtures (test DB, mocks)
├── unit/                    # Fast, isolated tests (no API calls)
│   ├── test_llm_logic.py
│   ├── test_slack_format.py
│   ├── test_retrieval_components.py
│   ├── test_sentence_gate.py
│   └── ...
└── integration/             # Real API calls (requires keys)
    ├── test_real_llm_search.py
    └── test_slack_integration.py
```

### Running Tests

```bash
# Run all tests (unit only, fast)
uv run pytest

# Run with coverage
uv run pytest --cov=technoshare_commentator

# Run unit tests explicitly
uv run pytest tests/unit/

# Run integration tests (requires API keys in .env)
RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration/

# Run specific test file
uv run pytest tests/unit/test_slack_format.py -v
```

### Configuration Verification

```bash
# Verify Slack/OpenAI credentials before running the bot
uv run python scripts/verify_config.py
```

📚 See [tests/README.md](tests/README.md) for detailed testing philosophy and guide.

---

## 🔬 Extraction Method Experiment

**Research Question**: Should we manually extract web content or give the LLM direct web access?

### Methodology

Compared two approaches on 4 diverse URLs (news, GitHub, arXiv, blog):

- **Method A (Ours)**: Fetch HTML → Extract clean text → Pass to LLM
- **Method B (Baseline)**: Give LLM the URL + web_search tool (OpenAI Responses API)

### Results Summary

| Metric | Method A (HTML) | Method B (web_search) | Winner |
|--------|-----------------|----------------------|--------|
| **Latency** | 17.75s | 26.83s | **A (51% faster)** |
| **Cost** | $0.0119 | $0.0580 | **A (5x cheaper)** |
| **Token Usage** | 1,133 in / 908 out | 17,418 in / 1,442 out | **A (15x less)** |
| **Quality Score** | 7.8/10 | 6.8/10 | **A (+1.0 point)** |
| **Success Rate** | 100% | 100% | Tie |

### Key Findings

✅ **Manual extraction wins across all dimensions**
- 51% faster (18s vs 27s)
- 5x cheaper ($0.012 vs $0.058 per analysis)
- Better quality (7.8/10 vs 6.8/10 term-grounded relevance)
- More focused (minimal drift to off-topic content)

❌ **Web search underperforms**
- Fetches 20+ external sources without improving accuracy
- Introduces drift to competitors/alternatives not on target page
- 15x higher token usage due to multi-source retrieval
- Slower due to multiple web requests during generation

**Conclusion**: Manual content curation (Method A) provides better cost, speed, quality, and control. Web search access adds complexity without measurable benefit.

📊 Full results: [`experiments/compare_extraction_methods/README.md`](experiments/compare_extraction_methods/README.md)

---

## 📚 Documentation

- [Slack Integration](src/technoshare_commentator/slack/README.md) - Socket Mode architecture
- [Architecture Diagrams](docs/ARCHITECTURE_DIAGRAMS.md) - Visual system overview

---
