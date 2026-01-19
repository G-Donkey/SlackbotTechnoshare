# MLflow LLMOps - Quick Reference

## Setup (One-Time)

```bash
# 1. Install dependencies
pip install -e .

# 2. Add to .env
echo "MLFLOW_TRACKING_URI=http://127.0.0.1:5000" >> .env
echo "MLFLOW_ENABLE_TRACKING=true" >> .env
echo "MLFLOW_ENABLE_TRACING=true" >> .env

# 3. Start MLflow server
./scripts/start_mlflow.sh
```

Open http://127.0.0.1:5000 to view UI.

---

## Daily Operations

### Start MLflow Server

```bash
# Foreground (recommended for dev)
./scripts/start_mlflow.sh

# Background
nohup ./scripts/start_mlflow.sh > mlflow.log 2>&1 &
```

### Run Pipeline (Auto-Logs to MLflow)

```bash
python -m technoshare_commentator.main_worker
```

### Sync Prompts After Changes

```bash
python scripts/sync_prompts.py
```

### Run Evaluation Suite

```bash
python scripts/run_eval.py
```

---

## What Gets Logged (Per Job)

### Automatically Tracked

- ✅ **Metrics**: Latency, token counts, gate pass/fail
- ✅ **Tags**: URL, domain, adapter, model names, outcome
- ✅ **Artifacts**: Evidence, facts, outputs, Slack payload
- ✅ **Traces**: Spans for retrieval, LLM calls, gates, posting

### View in MLflow UI

1. http://127.0.0.1:5000
2. Click `technoshare_commentator` experiment
3. Click any run to see details
4. Check "Traces" tab for LLM observability

---

## Key Commands

```bash
# View MLflow UI
open http://127.0.0.1:5000

# Stop MLflow server
pkill -f "mlflow server"

# Clean old runs (keep last 100)
mlflow gc --backend-store-uri sqlite:///mlflow.db

# Export run data
mlflow runs export --run-id <run_id> --output-dir ./exports

# Check server health
curl http://127.0.0.1:5000/health
```

---

## Filtering Runs in UI

| Filter | Example |
|--------|---------|
| Successful runs | `tags.outcome = 'success'` |
| Failed gates | `tags.outcome = 'gate_failed'` |
| Specific domain | `tags.domain = 'arxiv.org'` |
| Specific adapter | `tags.adapter_name = 'ArxivAdapter'` |
| High token usage | `metrics.tool_call_count > 0` |

---

## Evaluation Workflow

1. **Add examples** to `data/eval_dataset.json`
2. **Run suite**: `python scripts/run_eval.py`
3. **View results** in MLflow experiment `technoshare_eval`
4. **Check pass rate**: Look for `overall_pass_rate` metric
5. **Investigate failures**: Download artifacts from failed runs

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server won't start | Check port 5000: `lsof -i :5000`, use different port: `MLFLOW_PORT=5001 ./scripts/start_mlflow.sh` |
| No tracking data | Verify `MLFLOW_ENABLE_TRACKING=true` in .env |
| Artifacts missing | Check permissions: `chmod -R u+w mlartifacts/` |
| Eval fails | Run with debug: `LOG_LEVEL=DEBUG python scripts/run_eval.py` |

---

## Configuration Options

### Environment Variables

```bash
# MLflow server (defaults)
MLFLOW_TRACKING_URI=http://127.0.0.1:5000
MLFLOW_EXPERIMENT_NAME=technoshare_commentator

# Enable/disable features
MLFLOW_ENABLE_TRACKING=true   # Job tracking
MLFLOW_ENABLE_TRACING=true    # LLM tracing
```

### Startup Script Options

```bash
# Custom host/port
MLFLOW_HOST=0.0.0.0 MLFLOW_PORT=8080 ./scripts/start_mlflow.sh

# Custom backend (PostgreSQL)
MLFLOW_BACKEND_STORE=postgresql://user:pass@localhost/mlflow ./scripts/start_mlflow.sh

# Custom artifacts (S3)
MLFLOW_ARTIFACT_ROOT=s3://my-bucket/mlartifacts ./scripts/start_mlflow.sh
```

---

## File Locations

| What | Where |
|------|-------|
| MLflow DB | `./mlflow.db` |
| Artifacts | `./mlartifacts/` |
| Eval dataset | `data/eval_dataset.json` |
| Prompts | `data/prompts/*.yaml` |
| Scripts | `scripts/{start_mlflow,run_eval,sync_prompts}.sh|.py` |
| Docs | `docs/MLFLOW_GUIDE.md` |

---

## Next Steps After Setup

- [ ] Add 20+ real examples to `data/eval_dataset.json`
- [ ] Run baseline evaluation: `python scripts/run_eval.py`
- [ ] Process some Slack messages and verify tracking works
- [ ] Explore MLflow UI and get familiar with filtering
- [ ] Set up monitoring dashboard for key metrics
- [ ] Consider CI integration for automated eval checks

---

## Quick Links

- **MLflow UI**: http://127.0.0.1:5000
- **Full Guide**: `docs/MLFLOW_GUIDE.md`
- **MLflow Docs**: https://mlflow.org/docs/latest/

---

**Pro Tip**: Keep MLflow server running in a dedicated terminal window during development for real-time monitoring!
