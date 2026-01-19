"""Slack mrkdwn formatting for LLM outputs.

Converts Stage B results to Slack-compatible mrkdwn with proper
bold, lists, and section formatting.
"""

from __future__ import annotations

import re
from typing import List

from technoshare_commentator.llm.stage_b_schema import StageBResult

# Convert Markdown **bold** -> Slack *bold*
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def markdown_to_slack_mrkdwn(text: str) -> str:
    """
    Convert Markdown bold (**like this**) to Slack mrkdwn bold (*like this*).
    Keeps triple-backtick code blocks unchanged.
    """
    parts = re.split(r"(```[\s\S]*?```)", text)  # keep code blocks
    out: List[str] = []
    for p in parts:
        if p.startswith("```") and p.endswith("```"):
            out.append(p)
        else:
            out.append(_BOLD_RE.sub(r"*\1*", p))
    return "".join(out)


def _bullet_list(lines: List[str]) -> str:
    return "\n".join(f"• {s.strip()}" for s in lines if s and s.strip())


def _numbered_list(lines: List[str]) -> str:
    clean = [x.strip() for x in lines if x and x.strip()]
    return "\n".join(f"{i+1}) {s}" for i, s in enumerate(clean))


def render_stage_b_to_markdown(result: StageBResult) -> str:
    """
    Clean, scannable Markdown layout:
      - tldr: bullets
      - Summary: numbered lines
      - Projects: bullets
      - Similar tech: bullets or N/A
    Two blank lines between main sections (=> 3 newlines).
    """
    tldr_block = "**tldr**\n" + _bullet_list(result.tldr)
    summary_block = "**Summary**\n" + _numbered_list(result.summary)
    projects_block = "**Projects**\n" + _bullet_list(result.projects)

    if result.similar_tech:
        similar_block = "**Similar tech**\n" + _bullet_list(result.similar_tech)
    else:
        similar_block = "**Similar tech**\n• **N/A**"

    section_sep = "\n\n\n"  # two blank lines between sections
    return section_sep.join([tldr_block, summary_block, projects_block, similar_block])


def render_stage_b_to_slack(result: StageBResult) -> str:
    """
    End-to-end: StageBResult -> Slack mrkdwn text.
    """
    md = render_stage_b_to_markdown(result)
    return markdown_to_slack_mrkdwn(md)
