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

logger = logging.getLogger("pipeline")

class Pipeline:
    def process_job(self, job_id, channel_id, message_ts, text):
        logger.info(f"Processing job {job_id} for {channel_id}/{message_ts}")
        
        try:
            # 1. Identify URL
            urls = extract_urls(text)
            if not urls:
                logger.info("No URLs found during processing.")
                Repo.mark_job_done(job_id)
                return
            
            # For POC, pick first valid URL to summarize
            target_url = urls[0]
            logger.info(f"Target URL: {target_url}")
            
            # 2. Fetch Evidence (Adapter)
            adapter = get_adapter(target_url)
            evidence = adapter.fetch_evidence(target_url)
            
            if evidence.coverage == "failed":
                logger.warning("Fetch failed or rejected by adapter. Proceeding to Stage A to attempt Search Tool recovery.")
                # We do NOT return here; we let Stage A try to fix it with the search tool.
                
            # 3. Stage A (Facts)
            facts = run_stage_a(evidence)
            
            # 4. Stage B (Compose)
            context = load_project_context()
            reply_data = run_stage_b(facts, context)
            
            # 5. Quality Gates
            failures = run_quality_gates(reply_data)
            if failures:
                error_msg = f"Quality gate failed: {failures}"
                logger.error(error_msg)
                # For POC, logic to retry or just fail. We fail here.
                Repo.mark_job_failed(job_id, error_msg)
                return

            # 6-7. Validate, render and post via Block Kit (ensures mrkdwn rendering)
            post_stage_b_result(channel=channel_id, thread_ts=message_ts, result=reply_data)
            
            # 8. Mark Done
            Repo.mark_job_done(job_id)
            logger.info("Job completed successfully.")
            
        except Exception as e:
            logger.exception("Pipeline error")
            Repo.mark_job_failed(job_id, str(e))

pipeline = Pipeline()
