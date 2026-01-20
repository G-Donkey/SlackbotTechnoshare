"""Analysis result posting to Slack.

Renders LLM output to Slack mrkdwn format and posts as threaded reply.
"""

from __future__ import annotations

from typing import Optional
from technoshare_commentator.llm.schema import AnalysisResult
from technoshare_commentator.rendering.slack_format import render_analysis_to_slack
from technoshare_commentator.slack.post_blocks import build_post_payload
from technoshare_commentator.slack.client import slack_client


def post_analysis_result(channel: str, thread_ts: Optional[str], result: AnalysisResult) -> dict:
    """
    Render and post an AnalysisResult to Slack using Block Kit mrkdwn.
    Returns the payload that was posted for testing / logging.
    """
    slack_text = render_analysis_to_slack(result)
    payload = build_post_payload(channel=channel, text=slack_text, thread_ts=thread_ts)

    slack_client.post_payload(payload)
    return payload
