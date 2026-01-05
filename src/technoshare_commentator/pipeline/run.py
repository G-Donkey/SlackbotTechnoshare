import logging
from ..store.repo import Repo
from ..retrieval.url import extract_urls
from ..retrieval.adapters import get_adapter
from ..llm.stage_a import run_stage_a
from ..llm.stage_b import run_stage_b
from ..quality.gates import run_quality_gates
from ..config import load_project_context
from ..slack.client import slack_client

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
                logger.warning("Fetch failed, skipping reply.")
                Repo.mark_job_failed(job_id, f"Fetch failed: {evidence.errors}")
                return
                
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

            # 6. Format Reply
            final_text = self.format_slack_reply(reply_data, evidence)
            
            # 7. Post to Slack
            slack_client.post_reply(channel_id, message_ts, final_text)
            
            # 8. Mark Done
            Repo.mark_job_done(job_id)
            logger.info("Job completed successfully.")
            
        except Exception as e:
            logger.exception("Pipeline error")
            Repo.mark_job_failed(job_id, str(e))

    def format_slack_reply(self, data, evidence):
        """Convert StageBResult to Slack markdown."""
        lines = []
        
        # Summary
        for i, s in enumerate(data.summary_10_sentences, 1):
            lines.append(f"{i}. {s}")
        lines.append("")
        
        # Relevance
        lines.append("*How this helps our projects*")
        for item in data.project_relevance:
            lines.append(f"• {item}")
        lines.append("")
        
        # Risks
        lines.append("*Risks / Unknowns*")
        for item in data.risks_unknowns:
            lines.append(f"• {item}")
        
        if data.confidence < 0.55:
            lines.append("• _Manual review recommended_")
        lines.append("")
        
        # Next Step
        lines.append(f"*Next step*: {data.next_step}")
        lines.append("")
        
        # Sources
        lines.append("*Sources*")
        for source in evidence.sources:
            title = source.title or source.url
            lines.append(f"• <{source.url}|{title}>")
            
        return "\n".join(lines)

pipeline = Pipeline()
