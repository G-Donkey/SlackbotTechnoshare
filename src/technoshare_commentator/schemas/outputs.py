from __future__ import annotations
from pydantic import BaseModel, Field, confloat, model_validator
from typing import List
import re

from ..llm.stage_b_schema import StageBResult


class KeyFact(BaseModel):
    fact: str
    supported_by_snippet_ids: List[int]

class StageAResult(BaseModel):
    key_facts: List[KeyFact]
    unknowns: List[str]
    coverage_assessment: str # "full", "partial", "failed"

# StageBResult is defined in llm/stage_b_schema.py (single source of truth)


# Markdown → Slack mrkdwn converter
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")

def md_to_slack_mrkdwn(text: str) -> str:
    """
    Converteert **bold** (Markdown) naar *bold* (Slack mrkdwn).
    Laat code blocks (```...```) ongemoeid.
    """
    parts = re.split(r"(```[\s\S]*?```)", text)  # behoud codeblokken
    out = []
    for p in parts:
        if p.startswith("```") and p.endswith("```"):
            out.append(p)
        else:
            out.append(_BOLD_RE.sub(r"*\1*", p))
    return "".join(out)


def render_stage_b_to_slack(result: StageBResult) -> str:
    """
    Deterministische Slack mrkdwn renderer.
    Verwacht dat strings al de gewenste **vet** markering bevatten waar nuttig.
    Converteert automatisch **bold** naar *bold* voor Slack mrkdwn.
    """
    def join_sentences(lines: List[str]) -> str:
        # Bewaart exact de zinnen zoals gegeven, met spaties ertussen.
        return " ".join(s.strip() for s in lines if s.strip())

    def bullets(lines: List[str]) -> str:
        if not lines:
            return "• *N.v.t.*"
        return "\n".join(f"• {line.strip()}" for line in lines if line.strip())

    tldr_block = f"*tldr:* {join_sentences(result.tldr)}"
    summary_block = f"*Summary:* {join_sentences(result.summary)}"
    projects_block = f"*For which projects can this be relevant?:*\n{bullets(result.projects)}"
    similar_block = f"*Is there similar technology?:*\n{bullets(result.similar_tech)}"
    markdown_text = "\n\n".join([tldr_block, summary_block, projects_block, similar_block])
    
    # Convert Markdown **bold** to Slack *bold*
    return md_to_slack_mrkdwn(markdown_text)
