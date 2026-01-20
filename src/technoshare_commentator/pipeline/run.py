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
from ..slack.client import slack_client
from ..pipeline.post_analysis import post_analysis_result

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
            
            target_url = urls[0]
            logger.info(f"Target URL: {target_url}")
            
            # 2. Fetch Evidence (Adapter)
            adapter = get_adapter(target_url)
            evidence = adapter.fetch_evidence(target_url)
            
            if evidence.coverage == "failed":
                logger.warning("Fetch failed or rejected by adapter. Proceeding to analysis anyway.")
            
            # 3. Analysis (single LLM call - automatically traced by Langfuse via langfuse.openai)
            result = run_analysis(evidence)
            
            # 4. Quality Gates
            failures = run_quality_gates(result)
            
            if failures:
                error_msg = f"Quality gate failed: {failures}"
                logger.error(error_msg)
                Repo.mark_job_failed(job_id, error_msg)
                return

            # 5. Validate, render and post via Block Kit
            payload = post_analysis_result(channel=channel_id, thread_ts=message_ts, result=result)
            
            # Mark Done
            Repo.mark_job_done(job_id)
            logger.info("Job completed successfully.")
            
        except Exception as e:
            logger.exception("Pipeline error")
            Repo.mark_job_failed(job_id, str(e))

pipeline = Pipeline()
