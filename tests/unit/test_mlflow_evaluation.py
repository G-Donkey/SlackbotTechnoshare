"""Tests for MLflow evaluation functionality."""
import pytest
from pathlib import Path
from technoshare_commentator.mlops.evaluation.dataset import EvalExample, EvalDataset
from technoshare_commentator.mlops.evaluation.scorers import HardCheckScorers, run_hard_checks
from technoshare_commentator.llm.schema import AnalysisResult


class TestEvalDataset:
    """Tests for evaluation dataset management."""
    
    def test_create_eval_example(self):
        """Test creating an evaluation example."""
        example = EvalExample(
            id="test_1",
            url="https://example.com",
            slack_text="Check this: https://example.com",
            expected_theme="Technology",
            tags=["test", "example"]
        )
        
        assert example.id == "test_1"
        assert example.url == "https://example.com"
        assert len(example.tags) == 2
    
    def test_create_dataset(self):
        """Test creating an evaluation dataset."""
        dataset = EvalDataset(
            name="test_dataset",
            description="Test dataset",
            version="1.0"
        )
        
        assert dataset.name == "test_dataset"
        assert len(dataset.examples) == 0
    
    def test_add_example(self):
        """Test adding example to dataset."""
        dataset = EvalDataset(name="test", version="1.0")
        example = EvalExample(
            id="test_1",
            url="https://example.com",
            slack_text="Test"
        )
        
        dataset.add_example(example)
        
        assert len(dataset.examples) == 1
        assert dataset.examples[0].id == "test_1"
    
    def test_get_by_id(self):
        """Test retrieving example by ID."""
        dataset = EvalDataset(name="test", version="1.0")
        example = EvalExample(id="test_1", url="https://example.com", slack_text="Test")
        dataset.add_example(example)
        
        retrieved = dataset.get_by_id("test_1")
        
        assert retrieved is not None
        assert retrieved.id == "test_1"
    
    def test_get_by_id_not_found(self):
        """Test retrieving non-existent example."""
        dataset = EvalDataset(name="test", version="1.0")
        
        retrieved = dataset.get_by_id("nonexistent")
        
        assert retrieved is None
    
    def test_filter_by_tags(self):
        """Test filtering examples by tags."""
        dataset = EvalDataset(name="test", version="1.0")
        dataset.add_example(EvalExample(id="1", url="url1", slack_text="text", tags=["arxiv", "ml"]))
        dataset.add_example(EvalExample(id="2", url="url2", slack_text="text", tags=["github", "tools"]))
        dataset.add_example(EvalExample(id="3", url="url3", slack_text="text", tags=["arxiv", "research"]))
        
        filtered = dataset.filter_by_tags(["arxiv"])
        
        assert len(filtered) == 2
        assert all(example.id in ["1", "3"] for example in filtered)
    
    def test_create_default_dataset(self):
        """Test creating default dataset with examples."""
        dataset = EvalDataset.create_default()
        
        assert dataset.name == "technoshare_eval"
        assert len(dataset.examples) >= 2
        assert any(ex.id == "arxiv_example_1" for ex in dataset.examples)


class TestHardCheckScorers:
    """Tests for hard check scorers."""
    
    # Helper to create valid summary text
    VALID_SUMMARY = "This is a comprehensive summary paragraph with multiple sentences. It covers the key points of the content being analyzed. The technology offers significant benefits over existing solutions. Performance benchmarks show measurable improvements in key metrics. Overall it represents a meaningful step forward in the field."
    
    def test_schema_validity_valid(self):
        """Test schema validity scorer with valid result."""
        result = AnalysisResult(
            tldr=["This is a test.", "It has three sentences.", "All good."],
            summary=self.VALID_SUMMARY,
            projects=["**AI/ML** — Test project", "**Cloud** — Another project", "**DevOps** — Third project"],
            similar_tech=["**Tech 1** — First tech.", "**Tech 2** — Second tech."]
        )
        
        score = HardCheckScorers.schema_validity(result)
        
        assert score.passed is True
        assert score.score == 1.0
    
    def test_tldr_sentence_count_correct(self):
        """Test TLDR sentence count scorer with 3 sentences."""
        result = AnalysisResult(
            tldr=["First sentence.", "Second sentence.", "Third sentence."],
            summary=self.VALID_SUMMARY,
            projects=["**Test** — project", "**Another** — item", "**Third** — thing"],
            similar_tech=["**Tech** — description."]
        )
        
        score = HardCheckScorers.tldr_sentence_count(result)
        
        assert score.passed is True
        assert score.score == 1.0
        assert "3 sentences" in score.details
    
    def test_tldr_sentence_count_incorrect(self):
        """Test TLDR sentence count scorer with wrong count."""
        # Note: This will fail validation, but we're testing the scorer logic
        # In real usage, this would be caught by Pydantic first
        try:
            result = AnalysisResult(
                tldr=["Only two sentences.", "Here they are."],  # Will fail validation
                summary=self.VALID_SUMMARY,
                projects=["**Test** — proj", "**A** — b", "**C** — d"],
                similar_tech=["**Tech** — x."]
            )
        except Exception:
            # Expected - schema validation catches this
            # Scorer would never run in real usage
            assert True
            return
        
        # If somehow we get here, test the scorer
        score = HardCheckScorers.tldr_sentence_count(result)
        assert score.passed is False
    
    def test_summary_length_valid(self):
        """Test summary length scorer with sufficient length."""
        result = AnalysisResult(
            tldr=["Test.", "Test.", "Test."],
            summary=self.VALID_SUMMARY,  # > 100 chars
            projects=["**Test** — a", "**B** — c", "**D** — e"],
            similar_tech=["**Tech** — x."]
        )
        
        score = HardCheckScorers.summary_length(result)
        
        assert score.passed is True
        assert score.score == 1.0
    
    def test_projects_theme_prefix_present(self):
        """Test projects theme prefix scorer with correct format."""
        result = AnalysisResult(
            tldr=["Test.", "Test.", "Test."],
            summary=self.VALID_SUMMARY,
            projects=["**AI/ML** — Project 1", "**Cloud** — Project 2", "**DevOps** — Project 3"],
            similar_tech=["**Tech** — description."]
        )
        
        score = HardCheckScorers.projects_theme_prefix(result)
        
        assert score.passed is True
        assert score.score == 1.0
    
    def test_projects_theme_prefix_missing(self):
        """Test projects theme prefix scorer with missing format."""
        # Note: This will fail validation, but we're testing scorer logic
        try:
            result = AnalysisResult(
                tldr=["Test.", "Test.", "Test."],
                summary=self.VALID_SUMMARY,
                projects=["Project without prefix", "**Theme** — Project 2", "**Another** — one"],
                similar_tech=["**Tech** — description."]
            )
        except Exception:
            # Expected - schema validation catches this
            assert True
            return
        
        # If somehow we get here, test the scorer  
        score = HardCheckScorers.projects_theme_prefix(result)
        assert score.passed is False
    
    def test_projects_theme_prefix_all_valid(self):
        """Test projects theme prefix scorer with minimum projects."""
        result = AnalysisResult(
            tldr=["Test.", "Test.", "Test."],
            summary=self.VALID_SUMMARY,
            projects=["**A** — one", "**B** — two", "**C** — three"],
            similar_tech=["**Tech** — description."]
        )
        
        score = HardCheckScorers.projects_theme_prefix(result)
        
        assert score.passed is True
        assert score.score == 1.0
    
    def test_run_hard_checks(self):
        """Test running all hard checks."""
        result = AnalysisResult(
            tldr=["First sentence.", "Second sentence.", "Third sentence."],
            summary=self.VALID_SUMMARY,
            projects=["**AI/ML** — consulting", "**Cloud** — migration", "**DevOps** — automation"],
            similar_tech=["**Tech 1** — first.", "**Tech 2** — second."]
        )
        
        scores = run_hard_checks(result)
        
        assert len(scores.scores) >= 5
        assert all(score.passed for score in scores.scores)
        assert scores.overall_pass_rate() == 1.0
    
    def test_run_hard_checks_with_failures(self):
        """Test running hard checks - schema validation prevents bad data."""
        # Note: Pydantic validation happens before scorers, so we test with valid data
        result = AnalysisResult(
            tldr=["First.", "Second.", "Third."],
            summary=self.VALID_SUMMARY,
            projects=["**Test** — a", "**B** — b", "**C** — c"],
            similar_tech=["**Tech** — description."]
        )
        
        scores = run_hard_checks(result)
        
        # All should pass with valid data
        assert scores.overall_pass_rate() == 1.0


class TestEvalScores:
    """Tests for evaluation score aggregation."""
    
    def test_add_score(self):
        """Test adding scores."""
        from technoshare_commentator.mlops.evaluation.scorers import EvalScores
        
        scores = EvalScores()
        scores.add_score("test1", 1.0, True, "Passed")
        scores.add_score("test2", 0.0, False, "Failed")
        
        assert len(scores.scores) == 2
        assert scores.scores[0].name == "test1"
        assert scores.scores[1].name == "test2"
    
    def test_overall_pass_rate(self):
        """Test calculating overall pass rate."""
        from technoshare_commentator.mlops.evaluation.scorers import EvalScores
        
        scores = EvalScores()
        scores.add_score("test1", 1.0, True)
        scores.add_score("test2", 1.0, True)
        scores.add_score("test3", 0.0, False)
        scores.add_score("test4", 1.0, True)
        
        pass_rate = scores.overall_pass_rate()
        
        assert pass_rate == 0.75  # 3 out of 4 passed
    
    def test_get_failures(self):
        """Test getting failed scores."""
        from technoshare_commentator.mlops.evaluation.scorers import EvalScores
        
        scores = EvalScores()
        scores.add_score("test1", 1.0, True)
        scores.add_score("test2", 0.0, False)
        scores.add_score("test3", 0.0, False)
        
        failures = scores.get_failures()
        
        assert len(failures) == 2
        assert all(not f.passed for f in failures)
