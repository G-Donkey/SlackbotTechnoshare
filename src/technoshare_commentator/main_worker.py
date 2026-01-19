"""Background worker that processes jobs from the database queue.

Polls for pending jobs and executes the LLM pipeline for each.
Runs until interrupted (SIGINT).

Usage:
    python -m src.technoshare_commentator.main_worker
"""

import time
import signal
import sys
from .log import setup_logging, get_logger
from .config import get_settings
from .store.repo import Repo
from .pipeline.run import pipeline

setup_logging()
logger = get_logger("worker")

running = True

def handle_sigint(signum, frame):
    global running
    logger.info("Stopping worker...")
    running = False

def main():
    signal.signal(signal.SIGINT, handle_sigint)
    logger.info("Worker started. Polling for jobs...")
    
    while running:
        try:
            job = Repo.claim_next_job()
            if job:
                logger.info(f"Claimed job {job['id']}")
                pipeline.process_job(
                    job["id"], 
                    job["channel_id"], 
                    job["message_ts"], 
                    job["text"]
                )
            else:
                # Sleep briefly
                time.sleep(5)
        except Exception as e:
            logger.exception("Worker loop error")
            time.sleep(5)

if __name__ == "__main__":
    main()
