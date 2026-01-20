"""Main pipeline orchestrator for processing Slack messages.

Executes the 5-stage pipeline:
1. URL extraction
2. Evidence retrieval (via adapters)
3. Analysis (single LLM call)
4. Quality gates validation
5. Slack posting
"""

import logging
from ..store.repo import Repo
from ..retrieval.url import extract_urls
from ..retrieval.adapters import get_adapter
from ..llm.analyze import run_analysis
from ..quality.gates import run_quality_gates
from ..config import load_project_context
from ..slack.client import slack_client
from ..pipeline.post_analysis import post_analysis_result
from ..mlops.tracking import tracker
from ..mlops.tracing import tracer

logger = logging.getLogger("pipeline")

class Pipeline:
    def process_job(self, job_id, channel_id, message_ts, text):
        logger.info(f"Processing job {job_id} for {channel_id}/{message_ts}")
        
        # Extract URL early for tagging
        urls = extract_urls(text)
        target_url = urls[0] if urls else None
        
        # Start MLflow run for this job
        with tracker.start_job_run(
            job_id=job_id,
            channel_id=channel_id,
            message_ts=message_ts,
            target_url=target_url
        ) as run_id:
            try:
                # Log initial params
                tracker.log_params({
                    "job_id": job_id,
                    "channel_id": channel_id,
                    "message_ts": message_ts,
                }, run_id=run_id)
                
                # 1. Identify URL
                if not urls:
                    logger.info("No URLs found during processing.")
                    tracker.set_tags({"outcome": "no_urls"}, run_id=run_id)
                    Repo.mark_job_done(job_id)
                    return
                
                logger.info(f"Target URL: {target_url}")
                tracker.set_tags({"target_url": target_url}, run_id=run_id)
                
                # 2. Fetch Evidence (Adapter) with tracing
                with tracker.start_nested_run("retrieval", parent_run_id=run_id, tags={"stage": "retrieval"}) as retrieval_run_id:
                    with tracer.span("retrieval.fetch_evidence", span_type="RETRIEVER", inputs={"url": target_url}):
                        adapter = get_adapter(target_url)
                        evidence = adapter.fetch_evidence(target_url)
                        
                        # Log retrieval metadata
                        tracker.set_tags({
                            "adapter": adapter.__class__.__name__,
                            "coverage": evidence.coverage,
                            "has_errors": len(evidence.errors) > 0,
                        }, run_id=retrieval_run_id)
                        
                        tracker.log_metrics({
                            "snippet_count": len(evidence.snippets),
                            "source_count": len(evidence.sources),
                            "error_count": len(evidence.errors),
                        }, run_id=retrieval_run_id)
                        
                        # Log evidence artifact
                        tracker.log_dict_artifact(
                            evidence.model_dump(),
                            "evidence.json",
                            run_id=retrieval_run_id
                        )
                        
                        tracer.trace_retrieval(
                            url=target_url,
                            adapter_name=adapter.__class__.__name__,
                            coverage=evidence.coverage,
                            snippet_count=len(evidence.snippets)
                        )
                    
                    if evidence.coverage == "failed":
                        logger.warning("Fetch failed or rejected by adapter. Proceeding to analysis anyway.")
                
                # 3. Analysis (single LLM call) with tracing
                context = load_project_context()
                with tracker.start_nested_run("analysis", parent_run_id=run_id, tags={"stage": "analysis"}) as analysis_run_id:
                    with tracer.span("analysis.run", span_type="LLM"):
                        result = run_analysis(evidence, context)
                        
                        # Log analysis artifact
                        tracker.log_dict_artifact(
                            result.model_dump(),
                            "analysis_result.json",
                            run_id=analysis_run_id
                        )
                
                # 4. Quality Gates with tracing
                with tracker.start_nested_run("quality_gates", parent_run_id=run_id, tags={"stage": "quality_gates"}) as gates_run_id:
                    with tracer.span("quality_gates.validate", span_type="CHAIN"):
                        failures = run_quality_gates(result)
                        
                        tracker.log_metrics({
                            "gate_failures": len(failures),
                            "gate_passed": len(failures) == 0,
                        }, run_id=gates_run_id)
                        
                        if failures:
                            tracker.log_text_artifact(
                                "\n".join(failures),
                                "gate_failures.txt",
                                run_id=gates_run_id
                            )
                        
                        tracer.trace_quality_gates(failures, total_gates=5)  # Adjust total as needed
                        
                        if failures:
                            error_msg = f"Quality gate failed: {failures}"
                            logger.error(error_msg)
                            tracker.set_tags({"outcome": "gate_failed"}, run_id=run_id)
                            Repo.mark_job_failed(job_id, error_msg)
                            return

                # 5. Validate, render and post via Block Kit
                with tracker.start_nested_run("slack_post", parent_run_id=run_id, tags={"stage": "slack_post"}) as post_run_id:
                    with tracer.span("slack.post_message", span_type="CHAIN"):
                        payload = post_analysis_result(channel=channel_id, thread_ts=message_ts, result=result)
                        
                        # Log Slack payload
                        tracker.log_dict_artifact(
                            payload,
                            "slack_payload.json",
                            run_id=post_run_id
                        )
                
                # Mark Done
                Repo.mark_job_done(job_id)
                tracker.set_tags({"outcome": "success"}, run_id=run_id)
                logger.info("Job completed successfully.")
                
            except Exception as e:
                logger.exception("Pipeline error")
                tracker.set_tags({"outcome": "error", "error": str(e)}, run_id=run_id)
                Repo.mark_job_failed(job_id, str(e))

pipeline = Pipeline()
