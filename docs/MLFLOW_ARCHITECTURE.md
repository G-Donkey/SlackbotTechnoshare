# MLflow LLMOps Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    SLACK WORKSPACE                              │
│                                                                 │
│  User posts: "Check this out: https://arxiv.org/..."          │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INGEST SERVER (FastAPI)                       │
│                   Port 3000 / ngrok tunnel                      │
│                                                                 │
│  • Verify Slack signature                                      │
│  • Store job in SQLite                                         │
│  • Queue for processing                                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WORKER PROCESS                               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         Pipeline.process_job()                           │ │
│  │                                                          │ │
│  │  with tracker.start_job_run(job_id) as run_id:         │ │
│  │                                                          │ │
│  │    ┌──────────────────────────────────────────────────┐│ │
│  │    │  1. RETRIEVAL                                    ││ │
│  │    │     with tracer.span("retrieval.fetch"):        ││ │
│  │    │       • Get adapter (arxiv/github/generic)      ││ │
│  │    │       • Fetch content                           ││ │
│  │    │       • Log: snippets, coverage, domain         ││ │
│  │    └──────────────────────────────────────────────────┘│ │
│  │                         │                               │ │
│  │                         ▼                               │ │
│  │    ┌──────────────────────────────────────────────────┐│ │
│  │    │  2. STAGE A (Extract Facts)                     ││ │
│  │    │     with tracer.span("stage_a.run", "LLM"):    ││ │
│  │    │       • Run LLM with tools                      ││ │
│  │    │       • Search tool if needed                   ││ │
│  │    │       • Extract structured facts                ││ │
│  │    │       • Log: tools used, sources, tokens        ││ │
│  │    └──────────────────────────────────────────────────┘│ │
│  │                         │                               │ │
│  │                         ▼                               │ │
│  │    ┌──────────────────────────────────────────────────┐│ │
│  │    │  3. STAGE B (Compose Summary)                   ││ │
│  │    │     with tracer.span("stage_b.run", "LLM"):    ││ │
│  │    │       • Load project context                    ││ │
│  │    │       • Generate TLDR, Summary, Projects        ││ │
│  │    │       • Log: output structure                   ││ │
│  │    └──────────────────────────────────────────────────┘│ │
│  │                         │                               │ │
│  │                         ▼                               │ │
│  │    ┌──────────────────────────────────────────────────┐│ │
│  │    │  4. QUALITY GATES                               ││ │
│  │    │     with tracer.span("quality_gates"):          ││ │
│  │    │       • Sentence count checks                   ││ │
│  │    │       • Format validation                       ││ │
│  │    │       • Log: failures                           ││ │
│  │    └──────────────────────────────────────────────────┘│ │
│  │                         │                               │ │
│  │                         ▼                               │ │
│  │    ┌──────────────────────────────────────────────────┐│ │
│  │    │  5. SLACK POST                                  ││ │
│  │    │     with tracer.span("slack.post"):             ││ │
│  │    │       • Render to Slack blocks                  ││ │
│  │    │       • Post to thread                          ││ │
│  │    │       • Log: payload                            ││ │
│  │    └──────────────────────────────────────────────────┘│ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                           │                                   │
│                           │ All tracking/tracing data sent   │
└───────────────────────────┼───────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              MLflow TRACKING SERVER (Port 5000)                 │
│                                                                 │
│  ┌─────────────────────┐        ┌──────────────────────┐      │
│  │   Backend Store     │        │   Artifact Store     │      │
│  │   (SQLite)          │        │   (Local FS)         │      │
│  │                     │        │                      │      │
│  │  • Runs metadata    │        │  • evidence.json     │      │
│  │  • Params           │        │  • facts.json        │      │
│  │  • Metrics          │        │  • result.json       │      │
│  │  • Tags             │        │  • payload.json      │      │
│  │  • Traces           │        │  • failures.txt      │      │
│  └─────────────────────┘        └──────────────────────┘      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              MLflow Web UI                              │  │
│  │                                                         │  │
│  │  Experiments:                                          │  │
│  │    • technoshare_commentator  (main pipeline)         │  │
│  │    • technoshare_eval         (evaluation suite)      │  │
│  │                                                         │  │
│  │  Features:                                             │  │
│  │    • Run comparison                                    │  │
│  │    • Metric visualization                              │  │
│  │    • Trace inspection                                  │  │
│  │    • Artifact download                                 │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            ▲
                            │
                    Human views at
                http://127.0.0.1:5000
```

---

## Data Flow Detail

### Run Creation and Nesting

```
MLflow Experiment: technoshare_commentator
│
├── Run: job_abc123 (Parent)
│   │
│   ├── Tags:
│   │   • job_id: abc123
│   │   • channel_id: C123
│   │   • target_url: https://arxiv.org/abs/...
│   │   • outcome: success
│   │
│   ├── Nested Run: retrieval
│   │   ├── Tags: stage=retrieval, adapter_name=ArxivAdapter
│   │   ├── Metrics: latency_seconds=1.2, snippet_count=5
│   │   ├── Artifacts: evidence.json
│   │   └── Trace Span: retrieval.fetch_evidence
│   │
│   ├── Nested Run: stage_a
│   │   ├── Tags: stage=stage_a, model=gpt-4o
│   │   ├── Metrics: latency_seconds=3.5, tool_call_count=1
│   │   ├── Artifacts: stage_a_facts.json, sources.txt
│   │   └── Trace Span: stage_a.run (type: LLM)
│   │
│   ├── Nested Run: stage_b
│   │   ├── Tags: stage=stage_b, model=gpt-4o
│   │   ├── Metrics: latency_seconds=2.8
│   │   ├── Artifacts: stage_b_result.json
│   │   └── Trace Span: stage_b.run (type: LLM)
│   │
│   ├── Nested Run: quality_gates
│   │   ├── Tags: stage=quality_gates
│   │   ├── Metrics: gate_failures=0, gate_passed=1
│   │   ├── Artifacts: (none if all passed)
│   │   └── Trace Span: quality_gates.validate
│   │
│   └── Nested Run: slack_post
│       ├── Tags: stage=slack_post
│       ├── Metrics: latency_seconds=0.5
│       ├── Artifacts: slack_payload.json
│       └── Trace Span: slack.post_message
│
└── Run: job_xyz456 (Next job...)
```

---

## Trace Hierarchy

```
Trace: job_abc123
├── Span: retrieval.fetch_evidence (RETRIEVER, 1.2s)
│   └── Attributes:
│       • url: https://arxiv.org/abs/...
│       • adapter: ArxivAdapter
│       • coverage: full
│       • snippet_count: 5
│
├── Span: stage_a.run (LLM, 3.5s)
│   ├── Attributes:
│   │   • model: gpt-4o
│   │   • tool_calls: search
│   │   • tool_call_count: 1
│   │   • sources: https://arxiv.org/...
│   │   • source_count: 1
│   │
│   └── Child Span: search_tool_call (TOOL, 1.8s)
│       └── Attributes:
│           • url: https://arxiv.org/...
│           • content_length: 15432
│
├── Span: stage_b.run (LLM, 2.8s)
│   └── Attributes:
│       • model: gpt-4o
│       • prompt_length: 2500
│
├── Span: quality_gates.validate (CHAIN, 0.1s)
│   └── Attributes:
│       • gate_failures: 0
│       • gate_total: 5
│       • gate_pass_rate: 1.0
│
└── Span: slack.post_message (CHAIN, 0.5s)
```

---

## Evaluation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              EVALUATION SUITE (scripts/run_eval.py)             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Load Dataset (data/eval_dataset.json)              │
│                                                                 │
│  {                                                              │
│    "examples": [                                                │
│      {                                                          │
│        "id": "arxiv_example_1",                                 │
│        "url": "https://arxiv.org/abs/...",                      │
│        "slack_text": "Check this: ...",                         │
│        "expected_theme": "AI/ML",                               │
│        "tags": ["arxiv", "ml"]                                  │
│      },                                                         │
│      ...                                                        │
│    ]                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                   For each example:
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Run Pipeline (without posting to Slack)                │  │
│  │    • Fetch evidence                                     │  │
│  │    • Stage A                                            │  │
│  │    • Stage B                                            │  │
│  │    → Get StageBResult                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Apply Scorers                                          │  │
│  │    ✓ schema_validity                                    │  │
│  │    ✓ tldr_sentence_count (expect 3)                     │  │
│  │    ✓ summary_sentence_count (expect 10-15)             │  │
│  │    ✓ slack_formatting (two blank lines)                │  │
│  │    ✓ projects_theme_prefix ("Theme:" present)          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Calculate Scores                                       │  │
│  │    • Per-scorer: 0.0 or 1.0                            │  │
│  │    • Overall: pass_rate (% of scorers passed)          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Log to MLflow (Experiment: technoshare_eval)       │
│                                                                 │
│  Run: eval_suite                                                │
│    Params:                                                      │
│      • dataset_name: technoshare_eval                           │
│      • num_examples: 20                                         │
│                                                                 │
│    Metrics:                                                     │
│      • overall_pass_rate: 0.85                                  │
│      • total_examples: 20                                       │
│      • passed_examples: 17                                      │
│      • failed_examples: 3                                       │
│      • arxiv_example_1_pass_rate: 1.0                           │
│      • arxiv_example_1_schema_validity: 1.0                     │
│      • arxiv_example_1_tldr_sentence_count: 1.0                 │
│      • ...                                                      │
│                                                                 │
│    Artifacts:                                                   │
│      • eval_results.json (full results)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prompt Registry Flow

```
┌─────────────────────────────────────────────────────────────────┐
│         YAML Prompts (data/prompts/*.yaml)                      │
│                                                                 │
│  stage_a_extract_facts.yaml      ─────┐                        │
│  stage_b_compose_reply.yaml      ─────┤                        │
└───────────────────────────────────────┼─────────────────────────┘
                                        │
                                        ▼
                          scripts/sync_prompts.py
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              PromptRegistry.sync_prompts_from_yaml()            │
│                                                                 │
│  For each prompt:                                               │
│    1. Load YAML content                                         │
│    2. Compute content hash (SHA256[:12])                        │
│    3. Create MLflow run with:                                   │
│       • Tag: prompt_name                                        │
│       • Tag: content_hash                                       │
│       • Tag: source=yaml                                        │
│       • Artifact: prompts/{name}.txt                            │
└─────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MLflow Storage                               │
│                                                                 │
│  Runs with tags:                                                │
│    • prompt_name: stage_a_extract_facts                         │
│    • content_hash: a1b2c3d4e5f6                                 │
│    • timestamp: 2026-01-08 10:30:00                             │
│                                                                 │
│  Version History:                                               │
│    v1 (hash: abc123) - 2026-01-01                               │
│    v2 (hash: def456) - 2026-01-05                               │
│    v3 (hash: ghi789) - 2026-01-08 ← current                     │
└─────────────────────────────────────────────────────────────────┘
                                        │
                                        │ (Future: Alias promotion)
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│              Alias Management (Future)                          │
│                                                                 │
│  stage_a_extract_facts:                                         │
│    • prod      → v2 (hash: def456)                              │
│    • candidate → v3 (hash: ghi789)                              │
│    • staging   → v3 (hash: ghi789)                              │
│                                                                 │
│  Workflow:                                                      │
│    1. Edit YAML                                                 │
│    2. Sync (creates v3)                                         │
│    3. Run eval suite on v3                                      │
│    4. If passes: set candidate → v3                             │
│    5. If tests pass: promote prod → v3                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration Management

```
┌─────────────────────────────────────────────────────────────────┐
│                    .env File                                    │
│                                                                 │
│  # Required                                                     │
│  OPENAI_API_KEY=sk-...                                          │
│  SLACK_BOT_TOKEN=xoxb-...                                       │
│  SLACK_SIGNING_SECRET=...                                       │
│  TECHNOSHARE_CHANNEL_ID=C...                                    │
│                                                                 │
│  # MLflow (Optional - has defaults)                             │
│  MLFLOW_TRACKING_URI=http://127.0.0.1:5000                      │
│  MLFLOW_EXPERIMENT_NAME=technoshare_commentator                 │
│  MLFLOW_ENABLE_TRACKING=true                                    │
│  MLFLOW_ENABLE_TRACING=true                                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Settings (config.py)                               │
│                                                                 │
│  class Settings(BaseSettings):                                  │
│      # Slack                                                    │
│      SLACK_BOT_TOKEN: str                                       │
│      SLACK_SIGNING_SECRET: str                                  │
│      TECHNOSHARE_CHANNEL_ID: str                                │
│                                                                 │
│      # OpenAI                                                   │
│      OPENAI_API_KEY: str                                        │
│                                                                 │
│      # MLflow                                                   │
│      MLFLOW_TRACKING_URI: str = "http://127.0.0.1:5000"         │
│      MLFLOW_EXPERIMENT_NAME: str = "technoshare_commentator"    │
│      MLFLOW_ENABLE_TRACKING: bool = True                        │
│      MLFLOW_ENABLE_TRACING: bool = True                         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              MLflow Modules                                     │
│                                                                 │
│  • tracker.enabled = settings.MLFLOW_ENABLE_TRACKING            │
│  • tracer.enabled = settings.MLFLOW_ENABLE_TRACING              │
│                                                                 │
│  If disabled:                                                   │
│    → All tracking calls become no-ops                           │
│    → Pipeline continues without MLflow                          │
│    → No errors or exceptions                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## File System Layout

```
SlackbotTechnoshare/
├── mlflow.db                    ← MLflow backend (SQLite)
├── mlartifacts/                 ← MLflow artifacts (local)
│   ├── 0/                       ← Experiment ID
│   │   ├── abc123.../           ← Run ID
│   │   │   └── artifacts/
│   │   │       ├── evidence.json
│   │   │       ├── stage_a_facts.json
│   │   │       └── ...
│   │   └── ...
│   └── ...
│
├── data/
│   ├── eval_dataset.json        ← Evaluation examples
│   ├── prompts/
│   │   ├── stage_a_extract_facts.yaml
│   │   └── stage_b_compose_reply.yaml
│   └── ...
│
├── src/technoshare_commentator/
│   ├── mlops/                   ← MLflow integration
│   │   ├── __init__.py
│   │   ├── tracking.py          ← Job-level tracking
│   │   ├── tracing.py           ← LLM tracing
│   │   ├── prompt_registry.py   ← Prompt versioning
│   │   └── evaluation/          ← Eval harness
│   │       ├── __init__.py
│   │       ├── dataset.py
│   │       ├── scorers.py
│   │       └── runner.py
│   └── ...
│
├── scripts/
│   ├── start_mlflow.sh          ← Start tracking server
│   ├── run_eval.py              ← Run evaluation suite
│   └── sync_prompts.py          ← Sync prompts to registry
│
└── docs/
    ├── MLFLOW_GUIDE.md          ← Comprehensive guide
    ├── MLFLOW_QUICKSTART.md     ← Quick reference
    └── MLFLOW_CHECKLIST.md      ← Implementation checklist
```

---

This architecture provides:
- ✅ Complete observability of LLM operations
- ✅ Automatic tracking with zero code changes per job
- ✅ Evaluation framework for quality assurance
- ✅ Prompt versioning for safe iterations
- ✅ Graceful degradation when MLflow unavailable
- ✅ Production-ready with comprehensive documentation
