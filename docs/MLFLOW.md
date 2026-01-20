# MLflow LLMOps Integration

This document covers the MLflow-based observability and tracking setup for TechnoShare Commentator.

## Overview

MLflow provides:
- **Experiment Tracking**: Metrics, parameters, tags, and artifacts per job
- **LLM Observability**: Trace spans for retrieval, LLM calls, quality gates
- **Artifacts**: Stored evidence, facts, outputs, and Slack payloads

## Quick Start

### 1. Start MLflow Server

```bash
./scripts/start_mlflow.sh
```

Opens at http://127.0.0.1:5000

### 2. Configure Environment

Add to `.env`:

```bash
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MLFLOW_EXPERIMENT_NAME=technoshare_commentator
MLFLOW_ENABLE_TRACKING=true
MLFLOW_ENABLE_TRACING=true
```

### 3. Run Pipeline

MLflow automatically logs when you run:

```bash
python -m src.technoshare_commentator.main_worker
```

### 4. Disable MLflow (Optional)

```bash
export MLFLOW_ENABLE_TRACKING=false
export MLFLOW_ENABLE_TRACING=false
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Pipeline.process_job()                       │
│                                                                 │
│  with tracker.start_job_run(job_id) as run_id:                │
│                                                                 │
│    ┌─────────────────────────────────────────────────────────┐│
│    │  1. RETRIEVAL                                           ││
│    │     tracer.span("retrieval.fetch_evidence")            ││
│    │     → logs: adapter, coverage, snippet_count           ││
│    └─────────────────────────────────────────────────────────┘│
│                              ↓                                 │
│    ┌─────────────────────────────────────────────────────────┐│
│    │  2. ANALYSIS (Single LLM Call)                         ││
│    │     tracer.span("analysis.run", span_type="LLM")      ││
│    │     → logs: model, output structure                    ││
│    └─────────────────────────────────────────────────────────┘│
│                              ↓                                 │
│    ┌─────────────────────────────────────────────────────────┐│
│    │  3. QUALITY GATES                                      ││
│    │     tracer.span("quality_gates.validate")             ││
│    │     → logs: gate_failures, gate_passed                 ││
│    └─────────────────────────────────────────────────────────┘│
│                              ↓                                 │
│    ┌─────────────────────────────────────────────────────────┐│
│    │  4. SLACK POST                                         ││
│    │     tracer.span("slack.post_message")                 ││
│    │     → logs: payload                                    ││
│    └─────────────────────────────────────────────────────────┘│
│                                                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              MLflow Tracking Server (Port 5000)                 │
│                                                                 │
│   Backend Store (SQLite)     │     Artifact Store (Local)      │
│   • Runs, params, metrics    │     • evidence.json             │
│   • Tags, traces             │     • analysis_result.json      │
│                              │     • slack_payload.json        │
└─────────────────────────────────────────────────────────────────┘
```

---

## What Gets Logged

### Per Job (Parent Run)

| Type | Data |
|------|------|
| **Tags** | `job_id`, `channel_id`, `message_ts`, `target_url`, `outcome` |
| **Params** | Model settings |
| **Artifacts** | All stage outputs |

### Nested Runs

Each job creates nested runs for each stage:

```
job_xyz123 (parent)
├── retrieval (adapter, coverage, snippets)
├── analysis (model, output structure)
├── quality_gates (pass/fail counts)
└── slack_post (payload)
```

### Metrics

| Metric | Description |
|--------|-------------|
| `latency_seconds` | Per-stage latency |
| `snippet_count` | Retrieved content pieces |
| `tool_call_count` | Search tool invocations |
| `gate_failures` | Failed quality checks |

---

## MLflow UI Guide

### Filtering Runs

| Goal | Filter |
|------|--------|
| Successful runs | `tags.outcome = 'success'` |
| Failed gates | `tags.outcome = 'gate_failed'` |
| Specific domain | `tags.domain = 'arxiv.org'` |
| By adapter | `tags.adapter_name = 'ArxivAdapter'` |

### Viewing Traces

1. Open http://127.0.0.1:5000
2. Click `technoshare_commentator` experiment
3. Select a run
4. Click **"Traces"** tab to see LLM spans

---

## Server Management

```bash
# Start (foreground)
./scripts/start_mlflow.sh

# Start (background)
nohup ./scripts/start_mlflow.sh > mlflow.log 2>&1 &

# Check health
curl http://127.0.0.1:5000/health

# Stop
pkill -f "mlflow server"

# Clean old runs
mlflow gc --backend-store-uri sqlite:///mlflow.db
```

---

## Module Reference

### `mlops/tracking.py`

`MLflowTracker` - Handles experiment tracking:
- `start_job_run()` - Context manager for parent run
- `start_nested_run()` - Context manager for stage runs
- `log_params()`, `log_metrics()`, `set_tags()`
- `log_artifact()`, `log_dict_artifact()`, `log_text_artifact()`

### `mlops/tracing.py`

`MLflowTracer` - Handles LLM observability:
- `span()` - Context manager for traced spans
- `trace_retrieval()` - Log retrieval metrics
- `trace_llm_call()` - Log LLM invocations
- `trace_quality_gates()` - Log gate results

---

## Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MLFLOW_TRACKING_URI` | `http://127.0.0.1:5000` | MLflow server URL |
| `MLFLOW_EXPERIMENT_NAME` | `technoshare_commentator` | Experiment name |
| `MLFLOW_ENABLE_TRACKING` | `true` | Enable/disable tracking |
| `MLFLOW_ENABLE_TRACING` | `true` | Enable/disable tracing |
