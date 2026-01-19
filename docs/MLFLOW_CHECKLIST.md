# MLflow LLMOps Implementation Checklist

Use this checklist to verify your MLflow setup and track implementation progress.

## ✅ Phase 0: Infrastructure Setup

- [ ] **Dependencies Installed**
  ```bash
  pip install -e .
  # Verify MLflow is installed
  python -c "import mlflow; print(mlflow.__version__)"
  ```

- [ ] **MLflow Server Running**
  ```bash
  ./scripts/start_mlflow.sh
  # Check: curl http://127.0.0.1:5000/health
  ```

- [ ] **Environment Configured**
  ```bash
  # Added to .env:
  MLFLOW_TRACKING_URI=http://127.0.0.1:5000
  MLFLOW_ENABLE_TRACKING=true
  MLFLOW_ENABLE_TRACING=true
  ```

- [ ] **MLflow UI Accessible**
  - Open http://127.0.0.1:5000 in browser
  - Verify landing page loads

---

## ✅ Phase 1: Basic Tracking

- [ ] **First Tracked Run**
  ```bash
  # Process a job and verify it appears in MLflow
  python -m technoshare_commentator.main_worker
  ```
  - Check MLflow UI for new run in `technoshare_commentator` experiment
  - Verify run has tags: `job_id`, `channel_id`, `target_url`

- [ ] **Nested Runs Present**
  - Expand run in UI
  - Verify nested runs: `retrieval`, `stage_a`, `stage_b`, `quality_gates`, `slack_post`

- [ ] **Metrics Logged**
  - Each nested run shows `latency_seconds`
  - Stage A shows `tool_call_count`, `source_count`
  - Quality gates show `gate_failures`

- [ ] **Artifacts Present**
  - Click "Artifacts" tab
  - Verify files: `evidence.json`, `stage_a_facts.json`, `stage_b_result.json`, `slack_payload.json`

---

## ✅ Phase 2: Tracing

- [ ] **Traces Visible**
  - Click on a run
  - Navigate to "Traces" tab
  - Verify trace hierarchy exists

- [ ] **Span Hierarchy Correct**
  ```
  job_xyz
  ├── retrieval.fetch_evidence
  ├── stage_a.run
  ├── stage_b.run
  ├── quality_gates.validate
  └── slack.post_message
  ```

- [ ] **Span Attributes Present**
  - Click on `retrieval.fetch_evidence` span
  - Verify attributes: `url`, `adapter`, `coverage`, `snippet_count`
  - Click on `stage_a.run` span
  - Verify attributes: `model`, `tool_calls` (if tools used)

- [ ] **Latency Tracking**
  - Each span shows execution time
  - Can identify bottlenecks

---

## ✅ Phase 3: Prompt Registry

- [ ] **Prompts Synced**
  ```bash
  python scripts/sync_prompts.py
  ```
  - Check output shows version hashes for both prompts
  - Verify runs appear in MLflow with tag `prompt_name`

- [ ] **Prompt Artifacts in MLflow**
  - Find prompt sync runs
  - Check artifacts contain prompt text files

- [ ] **Version Tracking Works**
  - Modify a prompt in `data/prompts/`
  - Re-sync
  - Verify new version hash generated (different from previous)

---

## ✅ Phase 4: Evaluation Suite

- [ ] **Evaluation Dataset Exists**
  ```bash
  ls -la data/eval_dataset.json
  ```
  - File exists with at least 2 examples

- [ ] **Add Real Examples**
  - [ ] Add at least 5 real URLs from your Slack history
  - [ ] Include different domains (arxiv, github, blogs)
  - [ ] Add expected themes and tags

- [ ] **First Evaluation Run**
  ```bash
  python scripts/run_eval.py
  ```
  - Script completes without errors
  - Check MLflow UI for `technoshare_eval` experiment

- [ ] **Evaluation Results Present**
  - Switch to `technoshare_eval` experiment in UI
  - View latest run
  - Check metrics: `total_examples`, `passed_examples`, `overall_pass_rate`
  - Download `eval_results.json` artifact

- [ ] **Individual Scores Logged**
  - For each example, verify metrics exist:
    - `{example_id}_pass_rate`
    - `{example_id}_schema_validity`
    - `{example_id}_tldr_sentence_count`
    - `{example_id}_summary_sentence_count`

---

## ✅ Operational Readiness

- [ ] **Graceful Degradation**
  ```bash
  # Stop MLflow server
  pkill -f "mlflow server"
  
  # Run pipeline - should work without errors
  python -m technoshare_commentator.main_worker
  ```
  - Pipeline runs successfully
  - Logs show "MLflow tracking disabled" or similar

- [ ] **Cost Tracking** (Optional)
  - [ ] Add token cost calculation
  - [ ] Log `cost_usd` metric
  - [ ] Create dashboard view for cost over time

- [ ] **Filtering & Querying**
  - [ ] Filter runs by outcome: `tags.outcome = 'success'`
  - [ ] Filter by domain: `tags.domain = 'arxiv.org'`
  - [ ] Filter by adapter: `tags.adapter_name = 'ArxivAdapter'`
  - [ ] Filter failed gates: `metrics.gate_failures > 0`

- [ ] **Run Comparison**
  - [ ] Select 2+ runs in UI
  - [ ] Click "Compare"
  - [ ] View parameter differences
  - [ ] View metric charts side-by-side

---

## ✅ Documentation & Knowledge Transfer

- [ ] **Team Onboarding**
  - [ ] Share `docs/MLFLOW_QUICKSTART.md` with team
  - [ ] Demo MLflow UI navigation
  - [ ] Show how to investigate failed runs

- [ ] **CI Integration** (Future)
  - [ ] Add eval suite to GitHub Actions / CI pipeline
  - [ ] Fail builds on eval failures
  - [ ] Post results to PRs

- [ ] **Monitoring Setup** (Future)
  - [ ] Define alert thresholds (e.g., `gate_failures > 3`)
  - [ ] Set up notifications for degraded quality
  - [ ] Weekly eval suite runs scheduled

---

## 🎯 Success Criteria

You're ready for production when:

- ✅ Every pipeline run appears in MLflow with complete metadata
- ✅ Traces show detailed LLM observability with timing
- ✅ Evaluation suite passes with >80% overall_pass_rate on 20+ examples
- ✅ Prompts are versioned and changes are tracked
- ✅ Team can debug issues using MLflow artifacts and traces
- ✅ System degrades gracefully when MLflow is unavailable

---

## 📊 Key Metrics to Monitor

### Daily
- `overall_pass_rate` (eval suite) - Should stay >80%
- `gate_failures` per run - Trend should be stable or decreasing
- `latency_seconds` per stage - Watch for increases

### Weekly
- Total runs processed
- Distribution of `outcome` tags (success/gate_failed/error)
- Adapter coverage by domain
- Tool call frequency (Stage A search usage)

### Monthly
- Prompt version changes and impact on quality
- Cost per run (if tracking enabled)
- Failed example patterns in eval suite

---

## 🚨 Troubleshooting Checklist

If something isn't working:

1. **Check MLflow Server**
   ```bash
   curl http://127.0.0.1:5000/health
   # Should return 200 OK
   ```

2. **Check Environment Variables**
   ```bash
   python -c "from technoshare_commentator.config import get_settings; s = get_settings(); print(f'Tracking: {s.MLFLOW_ENABLE_TRACKING}, URI: {s.MLFLOW_TRACKING_URI}')"
   ```

3. **Check Logs**
   ```bash
   # Pipeline logs should show "MLflow tracking enabled"
   grep -i mlflow logs/worker.log
   ```

4. **Check Database**
   ```bash
   sqlite3 mlflow.db "SELECT count(*) FROM runs;"
   # Should return number of runs
   ```

5. **Check Artifacts**
   ```bash
   ls -la mlartifacts/
   # Should contain experiment folders
   ```

---

## 📚 Additional Resources

- [MLflow Tracking Guide](docs/MLFLOW_GUIDE.md)
- [Quick Reference](docs/MLFLOW_QUICKSTART.md)
- [Official MLflow Docs](https://mlflow.org/docs/latest/)
- [MLflow Tracing Tutorial](https://mlflow.org/docs/latest/llms/tracing/index.html)

---

**Next Steps After Completion:**

1. Run 10+ real jobs and verify tracking quality
2. Build custom dashboard for your key metrics
3. Add LLM judge scorers for soft quality checks
4. Integrate with your CI/CD pipeline
5. Consider distributed tracing for multi-agent scenarios

Happy tracking! 🚀
