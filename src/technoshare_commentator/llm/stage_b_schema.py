from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field, model_validator


class StageBResult(BaseModel):
    """
    LLM output = strict structured data.
    Strings may contain Markdown **bold**; Slack rendering happens later in code.
    """
    tldr: List[str] = Field(..., min_length=3, max_length=3, description="Exactly 3 full sentences.")
    summary: List[str] = Field(..., min_length=10, max_length=15, description="10–15 full sentences.")
    projects: List[str] = Field(..., min_length=3, max_length=8, description="3–8 bullets as strings.")
    similar_tech: List[str] = Field(default_factory=list, max_length=8, description="0–8 bullets as strings.")

    @model_validator(mode="after")
    def validate_constraints(self) -> "StageBResult":
        def is_full_sentence(s: str) -> bool:
            s = s.strip()
            if not s:
                return False
            # Check if sentence ends with punctuation (possibly followed by quotes/brackets)
            # Look at last few characters to be more lenient
            last_chars = s[-3:] if len(s) >= 3 else s
            return any(char in {".", "!", "?"} for char in last_chars)

        for s in self.tldr:
            if "\n" in s:
                raise ValueError(f"tldr items must not contain newlines -> {s!r}")
            if not is_full_sentence(s):
                raise ValueError(f"Each tldr item must end with .!? -> {s!r}")

        for s in self.summary:
            if "\n" in s:
                raise ValueError(f"Summary items must not contain newlines -> {s!r}")
            if not is_full_sentence(s):
                raise ValueError(f"Each Summary item must end with .!? -> {s!r}")

        for b in self.projects:
            # Each bullet should start with bold theme name like "**ThemeName** —"
            if not (b.strip().startswith("**") and "**" in b[3:] and " — " in b):
                raise ValueError(f"Each project bullet must start with '**ThemeName** — ...' -> {b!r}")

        return self
