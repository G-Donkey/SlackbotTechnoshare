"""Pydantic schema for LLM analysis output.

Defines AnalysisResult - the structured output from single-stage analysis.
"""

from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field, model_validator


class AnalysisResult(BaseModel):
    """
    LLM output from single-stage analysis.
    Strings may contain Markdown **bold**; Slack rendering happens later in code.
    """
    tldr: List[str] = Field(..., min_length=3, max_length=3, description="Exactly 3 full sentences.")
    summary: str = Field(..., min_length=100, description="Paragraph of text (5-10 sentences, no bullets).")
    projects: List[str] = Field(..., min_length=3, max_length=8, description="3–8 bullets as strings.")
    similar_tech: List[str] = Field(default_factory=list, max_length=8, description="0–8 bullets as strings.")

    @model_validator(mode="after")
    def validate_constraints(self) -> "AnalysisResult":
        def is_full_sentence(s: str) -> bool:
            s = s.strip()
            if not s:
                return False
            # Check if sentence ends with punctuation (possibly followed by quotes/brackets)
            last_chars = s[-3:] if len(s) >= 3 else s
            return any(char in {".", "!", "?"} for char in last_chars)

        for s in self.tldr:
            if "\n" in s:
                raise ValueError(f"tldr items must not contain newlines -> {s!r}")
            if not is_full_sentence(s):
                raise ValueError(f"Each tldr item must end with .!? -> {s!r}")

        # Summary is now a single text block - just verify it's not empty
        if not self.summary.strip():
            raise ValueError("Summary must not be empty")

        # Project bullets should just be non-empty strings
        for b in self.projects:
            if not b.strip():
                raise ValueError(f"Each project bullet must be non-empty")

        return self
