# TechnoShare Commentator

**AI-powered Slack bot for automated technical knowledge management.**

---

## 📖 Overview

TechnoShare Commentator monitors Slack channels for shared links, analyzes them using a single-stage LLM pipeline, and posts structured summaries as threaded replies.

### Key Features
- **🔌 Socket Mode**: WebSocket-based connection (no public URL required)
- **🧠 Single-Stage LLM Pipeline**: Combined analysis and composition in one call
- **📊 Langfuse Integration**: Optional tracking and tracing for LLM observability
- **⚡ Async Job Queue**: SQLite-backed queue with idempotent processing

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
│  │ (jobs table)  │       │                                  │
│  └───────────────┘       │                                  │
└─────────────────────────────────────────────────────────────┘
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

**Why single-stage?**
- **Faster**: ~3-5s total vs ~6-10s with two stages
- **Cheaper**: ~$0.01/link vs ~$0.02/link
- **Simpler**: One prompt to maintain, fewer failure points
- **Better context**: LLM sees full evidence when composing reply

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

The system runs as **two separate processes** for reliability:

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

## 🔬 Langfuse (Optional)

Enable LLM observability with Langfuse tracking and tracing.

### Setup
```bash
# Self-hosted Langfuse: docker-compose up -d
# Or use Langfuse Cloud: https://cloud.langfuse.com

# Add to .env
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_ENABLED=true
```

### What Gets Tracked
- **Traces**: Full pipeline runs with nested spans
- **LLM Calls**: Automatic OpenAI instrumentation (prompts, completions, tokens, cost)
- **Metrics**: Pipeline latency, token usage, quality gate results
- **Artifacts**: Evidence, analysis outputs logged as trace metadata

### Features
- Automatic OpenAI call tracing via `observe_openai` wrapper
- Decorator-based function tracing with `@observe`
- Prompt management and versioning
- Evaluation tracking with scores

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
- [Architecture Diagrams](docs/ARCHITECTURE_DIAGRAMS.md) - Visual system overview

---
