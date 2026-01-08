from __future__ import annotations

from typing import Optional
from technoshare_commentator.llm.stage_b_schema import StageBResult
from technoshare_commentator.rendering.slack_format import render_stage_b_to_slack
from technoshare_commentator.slack.post_blocks import build_post_payload
from technoshare_commentator.slack.client import slack_client


def post_stage_b_result(channel: str, thread_ts: Optional[str], result: StageBResult) -> dict:
    """
    Validate, render and post a StageBResult to Slack using Block Kit mrkdwn.
    Returns the payload that was posted for testing / logging.
    """
    # If result is already a StageBResult instance, use it directly
    # Otherwise validate it (useful for dict inputs in tests)
    if not isinstance(result, StageBResult):
        result = StageBResult.model_validate(result)

    slack_text = render_stage_b_to_slack(result)
    payload = build_post_payload(channel=channel, text=slack_text, thread_ts=thread_ts)

    slack_client.post_payload(payload)
    return payload
