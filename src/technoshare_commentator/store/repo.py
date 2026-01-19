"""Repository pattern for database operations.

Provides atomic operations for message storage and job queue management.
Handles idempotency via unique message timestamps.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from .db import get_db_connection
from tenacity import retry, stop_after_attempt, wait_fixed
import logging

logger = logging.getLogger("worker")

class Repo:
    @staticmethod
    def get_message_status(channel_id: str, message_ts: str) -> Optional[str]:
        """Check if we already know about this message (idempotency)."""
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT status FROM messages WHERE channel_id = ? AND message_ts = ?",
                (channel_id, message_ts)
            ).fetchone()
            return row["status"] if row else None

    @staticmethod
    def save_message(event: Dict[str, Any]) -> bool:
        """
        Save message and create a job if it's new.
        Returns True if newly inserted, False if duplicate.
        """
        try:
            with get_db_connection() as conn:
                # 1. Existence Check
                cursor = conn.execute(
                    "SELECT 1 FROM messages WHERE channel_id = ? AND message_ts = ?",
                    (event["channel"], event["ts"])
                )
                if cursor.fetchone():
                    return False

                # 2. Insert Message
                conn.execute(
                    """
                    INSERT INTO messages (channel_id, message_ts, thread_ts, user_id, text, status)
                    VALUES (?, ?, ?, ?, ?, 'received')
                    """,
                    (
                        event["channel"],
                        event["ts"],
                        event.get("thread_ts"),
                        event.get("user"),
                        event.get("text", "")
                    )
                )

                # 3. Create initial Job
                conn.execute(
                    """
                    INSERT INTO jobs (channel_id, message_ts, status)
                    VALUES (?, ?, 'pending')
                    """,
                    (event["channel"], event["ts"])
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"DB Error saving message: {e}")
            return False

    @staticmethod
    def claim_next_job() -> Optional[Dict[str, Any]]:
        """
        Atomic claim: find a pending job, mark it processing, return it.
        """
        with get_db_connection() as conn:
            # Immediate transaction
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Find pending
                row = conn.execute(
                    "SELECT id, channel_id, message_ts FROM jobs WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
                ).fetchone()
                
                if not row:
                    conn.rollback()
                    return None
                
                job_id = row["id"]
                conn.execute(
                    "UPDATE jobs SET status = 'processing', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (job_id,)
                )
                
                # Fetch full message content too
                msg_row = conn.execute(
                    "SELECT text FROM messages WHERE channel_id = ? AND message_ts = ?",
                    (row["channel_id"], row["message_ts"])
                ).fetchone()
                
                conn.commit()
                
                return {
                    "id": job_id,
                    "channel_id": row["channel_id"],
                    "message_ts": row["message_ts"],
                    "text": msg_row["text"] if msg_row else ""
                }
                
            except Exception as e:
                logger.error(f"Error claiming job: {e}")
                conn.rollback()
                return None

    @staticmethod
    def mark_job_done(job_id: int):
        with get_db_connection() as conn:
            conn.execute("UPDATE jobs SET status = 'done', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (job_id,))
            conn.commit()

    @staticmethod
    def mark_job_failed(job_id: int, error: str):
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE jobs SET status = 'failed', last_error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                (str(error), job_id)
            )
            conn.commit()
