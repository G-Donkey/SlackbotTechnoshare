import logging
from ..store.repo import Repo
from ..retrieval.url import extract_urls
from ..retrieval.adapters import get_adapter
from ..llm.stage_a import run_stage_a
from ..llm.stage_b import run_stage_b
from ..quality.gates import run_quality_gates
from ..config import load_project_context
from ..slack.client import slack_client
from ..pipeline.post_stage_b import post_stage_b_result
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
                        logger.warning("Fetch failed or rejected by adapter. Proceeding to Stage A to attempt Search Tool recovery.")
                
                # 3. Stage A (Facts) with tracing
                with tracker.start_nested_run("stage_a", parent_run_id=run_id, tags={"stage": "stage_a"}) as stage_a_run_id:
                    with tracer.span("stage_a.run", span_type="LLM"):
                        facts, meta = run_stage_a(evidence, return_meta=True)
                        
                        # Log Stage A metadata
                        tracker.set_tags({
                            "model": meta.model,
                            "tool_calls": ",".join(meta.tool_calls) if meta.tool_calls else "none",
                        }, run_id=stage_a_run_id)
                        
                        tracker.log_metrics({
                            "tool_call_count": len(meta.tool_calls),
                            "source_count": len(meta.sources),
                        }, run_id=stage_a_run_id)
                        
                        # Log facts artifact
                        tracker.log_dict_artifact(
                            facts.model_dump(),
                            "stage_a_facts.json",
                            run_id=stage_a_run_id
                        )
                        
                        # Trace tool usage
                        if meta.sources:
                            tracker.log_text_artifact(
                                "\n".join(meta.sources),
                                "sources.txt",
                                run_id=stage_a_run_id
                            )
                
                # 4. Stage B (Compose) with tracing
                context = load_project_context()
                with tracker.start_nested_run("stage_b", parent_run_id=run_id, tags={"stage": "stage_b"}) as stage_b_run_id:
                    with tracer.span("stage_b.run", span_type="LLM"):
                        reply_data = run_stage_b(facts, context)
                        
                        # Log Stage B artifact
                        tracker.log_dict_artifact(
                            reply_data.model_dump(),
                            "stage_b_result.json",
                            run_id=stage_b_run_id
                        )
                
                # 5. Quality Gates with tracing
                with tracker.start_nested_run("quality_gates", parent_run_id=run_id, tags={"stage": "quality_gates"}) as gates_run_id:
                    with tracer.span("quality_gates.validate", span_type="CHAIN"):
                        failures = run_quality_gates(reply_data)
                        
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

                # 6-7. Validate, render and post via Block Kit
                with tracker.start_nested_run("slack_post", parent_run_id=run_id, tags={"stage": "slack_post"}) as post_run_id:
                    with tracer.span("slack.post_message", span_type="CHAIN"):
                        payload = post_stage_b_result(channel=channel_id, thread_ts=message_ts, result=reply_data)
                        
                        # Log Slack payload
                        tracker.log_dict_artifact(
                            payload,
                            "slack_payload.json",
                            run_id=post_run_id
                        )
                
                # 8. Mark Done
                Repo.mark_job_done(job_id)
                tracker.set_tags({"outcome": "success"}, run_id=run_id)
                logger.info("Job completed successfully.")
                
            except Exception as e:
                logger.exception("Pipeline error")
                tracker.set_tags({"outcome": "error", "error": str(e)}, run_id=run_id)
                Repo.mark_job_failed(job_id, str(e))

pipeline = Pipeline()
