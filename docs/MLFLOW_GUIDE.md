# MLflow-based LLMOps for TechnoShare Commentator

This guide covers the complete MLflow-based LLMOps setup for TechnoShare Commentator, including tracking, tracing, prompt versioning, and evaluation.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Phase 0: MLflow Server Setup](#phase-0-mlflow-server-setup)
4. [Phase 1: Job-Level Tracking](#phase-1-job-level-tracking)
5. [Phase 2: LLM Tracing](#phase-2-llm-tracing)
6. [Phase 3: Prompt Registry](#phase-3-prompt-registry)
7. [Phase 4: Evaluation Suite](#phase-4-evaluation-suite)
8. [Configuration](#configuration)
9. [MLflow UI Guide](#mlflow-ui-guide)
10. [Best Practices](#best-practices)

---

## Overview

### What You Get

For every processed Slack link/job, you'll have:

1. **Experiment Tracking**: Run with params/tags/metrics + artifacts (prompts, evidence, outputs, gate results)
2. **LLM Observability Tracing**: Trace with spans for Stage A, Stage B, retrieval, tool calls, and Slack posting
3. **Prompt Versioning**: Stage A & B prompts versioned + aliased (e.g., prod, candidate) for safe rollout
4. **Evaluation Harness**: Suite that scores summary quality, structure compliance, and business relevance

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MLflow Tracking Server                    │
│              (SQLite backend + local artifacts)              │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ┌───────▼──────┐    ┌──────▼──────┐
            │   Tracking   │    │   Tracing   │
            │   (Metrics)  │    │   (Spans)   │
            └──────────────┘    └─────────────┘
                    │                   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼──────────┐
                    │  Pipeline Runner   │
                    │  (process_job)     │
                    └────────────────────┘
```

---

## Quick Start

### 1. Install Dependencies

```bash
# Install all dependencies including MLflow
pip install -e .
```

### 2. Start MLflow Server

```bash
# Start the MLflow tracking server
./scripts/start_mlflow.sh
```

This will start MLflow at http://127.0.0.1:5000 with:
- Backend store: SQLite (`mlflow.db`)
- Artifact store: Local folder (`./mlartifacts`)

### 3. Configure Environment

Add to your `.env` file:

```bash
# MLflow Configuration
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MLFLOW_EXPERIMENT_NAME=technoshare_commentator
MLFLOW_ENABLE_TRACKING=true
MLFLOW_ENABLE_TRACING=true
```

### 4. Run Your Pipeline

The pipeline will automatically log to MLflow:

```bash
# Start your worker as usual
python -m technoshare_commentator.main_worker
```

### 5. View Results

Open http://127.0.0.1:5000 in your browser to see:
- All runs with metrics and artifacts
- Traces with LLM spans
- Evaluation results

---

## Phase 0: MLflow Server Setup

### Starting the Server

The startup script supports customization via environment variables:

```bash
# Default (SQLite + local artifacts)
./scripts/start_mlflow.sh

# Custom host/port
MLFLOW_HOST=0.0.0.0 MLFLOW_PORT=8080 ./scripts/start_mlflow.sh

# Custom backend and artifacts
MLFLOW_BACKEND_STORE=postgresql://user:pass@localhost/mlflow \
MLFLOW_ARTIFACT_ROOT=s3://my-bucket/mlartifacts \
./scripts/start_mlflow.sh
```

### Server Management

```bash
# Start in background
nohup ./scripts/start_mlflow.sh > mlflow.log 2>&1 &

# Check if running
curl http://127.0.0.1:5000/health

# Stop server
pkill -f "mlflow server"
```

---

## Phase 1: Job-Level Tracking

### What Gets Tracked

Every job run logs:

**Tags**
- `job_id`, `channel_id`, `message_ts`
- `target_url`, `domain`, `adapter_name`, `coverage`
- `stage_a_model`, `stage_b_model`
- `outcome` (success/gate_failed/error)

**Params**
- Model settings (temperature, max_tokens)
- Quality gate config

**Metrics**
- `latency_seconds` per stage
- `tool_call_count`, `source_count`
- `gate_failures`, `gate_passed`
- `snippet_count`

**Artifacts**
- `evidence.json` - Retrieved content
- `stage_a_facts.json` - Extracted facts
- `stage_b_result.json` - Final output
- `slack_payload.json` - Posted message
- `gate_failures.txt` - Failed quality gates
- `sources.txt` - Tool-fetched URLs

### Nested Run Structure

Each job creates nested runs:

```
job_xyz123 (parent run)
├── retrieval (nested)
├── stage_a (nested)
├── stage_b (nested)
├── quality_gates (nested)
└── slack_post (nested)
```

### Querying Runs

```python
import mlflow

# Get all successful runs
client = mlflow.tracking.MlflowClient()
runs = client.search_runs(
    experiment_ids=["0"],
    filter_string="tags.outcome = 'success'"
)

# Get runs with quality gate failures
failed_runs = client.search_runs(
    experiment_ids=["0"],
    filter_string="tags.outcome = 'gate_failed'"
)
```

---

## Phase 2: LLM Tracing

### Traced Operations

The following operations are traced with spans:

1. **retrieval.fetch_evidence**
   - Attributes: url, adapter, coverage, snippet_count
   
2. **stage_a.run**
   - Type: LLM
   - Attributes: model, tool_calls, sources
   
3. **stage_b.run**
   - Type: LLM
   - Attributes: model
   
4. **quality_gates.validate**
   - Type: CHAIN
   - Attributes: gate_failures, gate_pass_rate
   
5. **slack.post_message**
   - Type: CHAIN

### Viewing Traces

In MLflow UI:
1. Navigate to an experiment run
2. Click on "Traces" tab
3. Explore the span hierarchy
4. View inputs/outputs and attributes

### Adding Custom Spans

```python
from technoshare_commentator.mlops.tracing import tracer

with tracer.span("my_operation", span_type="TOOL", attributes={"key": "value"}):
    # Your code here
    pass
```

---

## Phase 3: Prompt Registry

### Syncing Prompts to MLflow

Register your YAML prompts in MLflow:

```bash
# Sync all prompts
python scripts/sync_prompts.py
```

This creates versioned entries for:
- `stage_a_extract_facts`
- `stage_b_compose_reply`

Each version gets a content hash for tracking changes.

### Prompt Versioning Workflow

1. **Edit Prompt**: Modify YAML file
2. **Sync**: Run `sync_prompts.py`
3. **Test**: Run evaluation suite
4. **Promote**: Set alias (future: `prod`, `candidate`)

### Loading Prompts

Currently falls back to YAML, but registry-aware:

```python
from technoshare_commentator.mlops.prompt_registry import prompt_registry

# Load prompt (currently from YAML, registry support ready)
prompt = prompt_registry.load_prompt(
    "stage_a_extract_facts",
    alias="prod",
    fallback_to_yaml=True
)
```

### Future: Alias Management

```python
# Set production alias (when fully implemented)
prompt_registry.set_alias(
    name="stage_a_extract_facts",
    version_hash="abc123",
    alias="prod"
)
```

---

## Phase 4: Evaluation Suite

### Creating an Evaluation Dataset

The system auto-creates a default dataset at `data/eval_dataset.json`:

```json
{
  "name": "technoshare_eval",
  "description": "Evaluation dataset for TechnoShare Commentator",
  "version": "1.0",
  "examples": [
    {
      "id": "arxiv_example_1",
      "url": "https://arxiv.org/abs/2401.00001",
      "slack_text": "Check this out: https://arxiv.org/abs/2401.00001",
      "expected_theme": "AI/ML",
      "tags": ["arxiv", "ml"]
    }
  ]
}
```

### Adding Examples

Edit `data/eval_dataset.json` to add real examples from your Slack history:

```json
{
  "id": "real_example_1",
  "url": "https://github.com/microsoft/vscode",
  "slack_text": "Interesting project: https://github.com/microsoft/vscode",
  "expected_theme": "Development Tools",
  "notes": "VSCode repository - should extract editor features",
  "tags": ["github", "tools", "editor"]
}
```

### Running Evaluation

```bash
# Run full evaluation suite
python scripts/run_eval.py
```

This will:
1. Load all examples from dataset
2. Run pipeline on each
3. Score outputs with hard checks
4. Log results to MLflow experiment `technoshare_eval`

### Evaluation Scores

**Hard Checks (Automated)**:
- `schema_validity` - Valid StageBResult
- `tldr_sentence_count` - Exactly 3 sentences
- `summary_sentence_count` - 10-15 sentences
- `slack_formatting` - Two blank lines between sections
- `projects_theme_prefix` - "Theme:" prefix on projects

### Viewing Evaluation Results

In MLflow UI:
1. Switch to `technoshare_eval` experiment
2. View runs sorted by `overall_pass_rate`
3. Click run to see:
   - Individual example scores
   - Failed checks
   - Aggregate metrics

### CI Integration (Future)

```bash
# In CI pipeline
python scripts/run_eval.py
if [ $? -ne 0 ]; then
  echo "Evaluation failed! Do not merge."
  exit 1
fi
```

---

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
TECHNOSHARE_CHANNEL_ID=C...

# MLflow (with defaults)
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MLFLOW_EXPERIMENT_NAME=technoshare_commentator
MLFLOW_ENABLE_TRACKING=true
MLFLOW_ENABLE_TRACING=true
```

### Disabling MLflow

To disable tracking/tracing:

```bash
MLFLOW_ENABLE_TRACKING=false
MLFLOW_ENABLE_TRACING=false
```

The system gracefully degrades - all MLflow calls become no-ops.

---

## MLflow UI Guide

### Main Dashboard

http://127.0.0.1:5000

- **Experiments**: List of all experiments
- **Models**: Registered models (for prompt registry)
- **Compare**: Compare multiple runs side-by-side

### Experiment View

Click on `technoshare_commentator` experiment:

- **Table View**: All runs with metrics
- **Chart View**: Visualize metrics over time
- **Parallel Coordinates**: Compare parameters

### Run Detail View

Click on a specific run:

- **Overview**: Tags, params, metrics summary
- **Metrics**: Time-series metrics with charts
- **Artifacts**: Download logged files
- **Traces**: Span hierarchy with timing

### Filtering Runs

Use the filter syntax:

```
# Successful runs only
tags.outcome = 'success'

# ArXiv papers
tags.domain = 'arxiv.org'

# Failed quality gates
metrics.gate_failures > 0

# Specific adapter
tags.adapter_name = 'ArxivAdapter'
```

### Comparing Runs

1. Select multiple runs (checkboxes)
2. Click "Compare"
3. View side-by-side:
   - Parameters diff
   - Metrics charts
   - Artifact diffs

---

## Best Practices

### 1. Regular Evaluation

Run evaluation suite:
- After prompt changes
- Before deploying
- Weekly for regression checks

```bash
# Add to crontab
0 9 * * 1 cd /path/to/project && python scripts/run_eval.py
```

### 2. Monitor Key Metrics

Watch for:
- `gate_failures` trending up → Quality issues
- `tool_call_count` trending up → Evidence quality degrading
- `latency_seconds` trending up → Performance issues

### 3. Artifact Management

Artifacts are stored locally in `./mlartifacts/`. Consider:
- Regular cleanup of old runs
- Backup important artifacts
- Archive to S3 for long-term storage

```bash
# Clean up old runs (keep last 100)
mlflow gc --backend-store-uri sqlite:///mlflow.db
```

### 4. Prompt Versioning

Before making prompt changes:
1. Note current version hash
2. Make changes to YAML
3. Sync to registry
4. Run evaluation
5. If passes, consider it "promoted"
6. If fails, revert YAML

### 5. Tagging Strategy

Use consistent tags:
- `job_id` - Always include for traceability
- `target_url` - For URL-based analysis
- `domain` - For adapter performance
- `outcome` - For success/failure tracking

### 6. Cost Tracking

Add cost estimation:

```python
# In your pipeline
prompt_tokens = 1000
completion_tokens = 500
cost = (prompt_tokens * 0.005 + completion_tokens * 0.015) / 1000
tracker.log_metrics({"cost_usd": cost}, run_id=run_id)
```

### 7. Debugging with Traces

When investigating issues:
1. Find the failed run in MLflow
2. Open Traces tab
3. Identify slow/failing spans
4. Download artifacts for that span
5. Inspect inputs/outputs

---

## Troubleshooting

### MLflow Server Won't Start

```bash
# Check if port is in use
lsof -i :5000

# Try different port
MLFLOW_PORT=5001 ./scripts/start_mlflow.sh
```

### Tracking Not Working

```bash
# Verify connection
python -c "import mlflow; mlflow.set_tracking_uri('http://127.0.0.1:5000'); print(mlflow.get_tracking_uri())"

# Check server logs
tail -f mlflow.log
```

### Artifacts Not Appearing

```bash
# Check artifact location
ls -la mlartifacts/

# Verify permissions
chmod -R u+w mlartifacts/
```

### Evaluation Failing

```bash
# Run with verbose logging
LOG_LEVEL=DEBUG python scripts/run_eval.py

# Test single example
python -c "
from technoshare_commentator.mlops.evaluation.dataset import load_or_create_dataset
from pathlib import Path
ds = load_or_create_dataset(Path('data/eval_dataset.json'))
print(ds.examples[0])
"
```

---

## Next Steps

1. **Expand Evaluation Dataset**: Add 20-50 real examples from Slack
2. **Add LLM Judges**: Implement soft checks (faithfulness, relevance)
3. **Cost Dashboard**: Add OpenAI API cost tracking
4. **Full Prompt Registry**: Implement alias-based loading
5. **CI Integration**: Fail PRs on eval failures
6. **Alerting**: Set up alerts on metric thresholds

---

## References

- [MLflow Tracking Docs](https://mlflow.org/docs/latest/tracking.html)
- [MLflow Tracing Docs](https://mlflow.org/docs/latest/llms/tracing/index.html)
- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)
- [MLflow GenAI Evaluation](https://mlflow.org/docs/latest/llms/llm-evaluate/index.html)

---

## Support

For issues or questions:
1. Check MLflow UI for error details
2. Review pipeline logs
3. Inspect run artifacts
4. Enable DEBUG logging for detailed traces

Happy tracking! 🚀
