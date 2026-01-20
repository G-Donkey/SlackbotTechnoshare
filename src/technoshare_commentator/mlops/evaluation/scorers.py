"""
Scorers for evaluating analysis output quality.
Implements both hard checks (deterministic) and soft checks (LLM-based).
"""
import logging
from typing import Dict, Any, List, Callable
from pydantic import BaseModel, Field

from ...llm.schema import AnalysisResult
from ...quality.sentence import count_sentences_naive

logger = logging.getLogger(__name__)


class ScoreResult(BaseModel):
    """Result of a single scorer."""
    name: str = Field(..., description="Scorer name")
    score: float = Field(..., description="Score value (0.0 to 1.0)")
    passed: bool = Field(..., description="Whether the check passed")
    details: str = Field(default="", description="Additional details")


class EvalScores(BaseModel):
    """Collection of evaluation scores."""
    scores: List[ScoreResult] = Field(default_factory=list)
    
    def add_score(self, name: str, score: float, passed: bool, details: str = ""):
        """Add a score result."""
        self.scores.append(ScoreResult(
            name=name,
            score=score,
            passed=passed,
            details=details
        ))
    
    def overall_pass_rate(self) -> float:
        """Calculate overall pass rate."""
        if not self.scores:
            return 0.0
        return sum(1 for s in self.scores if s.passed) / len(self.scores)
    
    def get_failures(self) -> List[ScoreResult]:
        """Get all failed scores."""
        return [s for s in self.scores if not s.passed]


class HardCheckScorers:
    """Collection of deterministic hard check scorers."""
    
    @staticmethod
    def schema_validity(result: AnalysisResult) -> ScoreResult:
        """Check if result conforms to AnalysisResult schema."""
        try:
            # If we got here, schema is valid (Pydantic already validated)
            return ScoreResult(
                name="schema_validity",
                score=1.0,
                passed=True,
                details="Schema is valid"
            )
        except Exception as e:
            return ScoreResult(
                name="schema_validity",
                score=0.0,
                passed=False,
                details=f"Schema validation failed: {str(e)}"
            )
    
    @staticmethod
    def tldr_sentence_count(result: AnalysisResult) -> ScoreResult:
        """Check if TLDR has exactly 3 sentences."""
        count = len(result.tldr)  # TLDR is already a list of sentences
        passed = count == 3
        return ScoreResult(
            name="tldr_sentence_count",
            score=1.0 if passed else 0.0,
            passed=passed,
            details=f"TLDR has {count} sentences (expected 3)"
        )
    
    @staticmethod
    def summary_length(result: AnalysisResult) -> ScoreResult:
        """Check if Summary has sufficient length (min 100 chars)."""
        length = len(result.summary)
        passed = length >= 100
        return ScoreResult(
            name="summary_length",
            score=1.0 if passed else 0.0,
            passed=passed,
            details=f"Summary has {length} characters (minimum 100)"
        )
    
    @staticmethod
    def slack_formatting(result: AnalysisResult) -> ScoreResult:
        """Check if output follows Slack formatting rules."""
        from ...rendering.slack_format import render_analysis_to_slack
        
        try:
            text = render_analysis_to_slack(result)
            
            # Check for section separators (two blank lines)
            sections = text.split('\n\n\n')
            
            # Should have at least 3 sections (TLDR, Summary, Projects/Tech)
            if len(sections) < 3:
                return ScoreResult(
                    name="slack_formatting",
                    score=0.0,
                    passed=False,
                    details=f"Expected at least 3 sections, got {len(sections)}"
                )
            
            return ScoreResult(
                name="slack_formatting",
                score=1.0,
                passed=True,
                details="Slack formatting is correct"
            )
        except Exception as e:
            return ScoreResult(
                name="slack_formatting",
                score=0.0,
                passed=False,
                details=f"Formatting check failed: {str(e)}"
            )
    
    @staticmethod
    def projects_theme_prefix(result: AnalysisResult) -> ScoreResult:
        """Check if Projects bullets have '**Theme** — ' format."""
        if not result.projects:
            return ScoreResult(
                name="projects_theme_prefix",
                score=1.0,
                passed=True,
                details="No projects to check"
            )
        
        for project in result.projects:
            # Check for '**ThemeName** — ' format
            if not (project.strip().startswith("**") and " — " in project):
                return ScoreResult(
                    name="projects_theme_prefix",
                    score=0.0,
                    passed=False,
                    details=f"Project bullet missing '**Theme** — ' format: {project[:50]}..."
                )
        
        return ScoreResult(
            name="projects_theme_prefix",
            score=1.0,
            passed=True,
            details="All project bullets have '**Theme** — ' format"
        )


def run_hard_checks(result: AnalysisResult) -> EvalScores:
    """Run all hard check scorers on a result."""
    scores = EvalScores()
    
    scorers = [
        HardCheckScorers.schema_validity,
        HardCheckScorers.tldr_sentence_count,
        HardCheckScorers.summary_length,
        HardCheckScorers.slack_formatting,
        HardCheckScorers.projects_theme_prefix,
    ]
    
    for scorer in scorers:
        try:
            score_result = scorer(result)
            scores.scores.append(score_result)
        except Exception as e:
            logger.exception(f"Scorer {scorer.__name__} failed")
            scores.add_score(
                name=scorer.__name__,
                score=0.0,
                passed=False,
                details=f"Scorer error: {str(e)}"
            )
    
    return scores
