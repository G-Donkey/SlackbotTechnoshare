"""
Evaluation runner for TechnoShare Commentator.
Runs evaluation suite and logs results to MLflow.
"""
import logging
from typing import Optional, List
from pathlib import Path

import mlflow

from .dataset import EvalDataset, EvalExample, load_or_create_dataset
from .scorers import run_hard_checks, EvalScores
from ...pipeline.run import Pipeline
from ...llm.schema import AnalysisResult
from ...config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EvalRunner:
    """Runs evaluation suite and logs to MLflow."""
    
    def __init__(self, dataset_path: Optional[Path] = None):
        if dataset_path is None:
            dataset_path = Path("data/eval_dataset.json")
        self.dataset = load_or_create_dataset(dataset_path)
        self.pipeline = Pipeline()
    
    def run_example(self, example: EvalExample) -> tuple[Optional[AnalysisResult], EvalScores]:
        """
        Run a single evaluation example.
        Returns the result and scores.
        """
        try:
            # For evaluation, we need to simulate the pipeline without actually posting to Slack
            from ...retrieval.url import extract_urls
            from ...retrieval.adapters import get_adapter
            from ...llm.analyze import run_analysis
            from ...config import load_project_context
            
            # Extract URL
            urls = extract_urls(example.slack_text)
            if not urls:
                logger.warning(f"No URLs found in example {example.id}")
                return None, EvalScores()
            
            target_url = urls[0]
            
            # Fetch evidence
            adapter = get_adapter(target_url)
            evidence = adapter.fetch_evidence(target_url)
            
            # Single-stage analysis
            context = load_project_context()
            result = run_analysis(evidence, context)
            
            # Score the result
            scores = run_hard_checks(result)
            
            return result, scores
            
        except Exception as e:
            logger.exception(f"Failed to run example {example.id}")
            return None, EvalScores()
    
    def run_evaluation(
        self,
        example_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        experiment_name: str = "technoshare_eval"
    ) -> dict:
        """
        Run evaluation suite and log to MLflow.
        
        Args:
            example_ids: Specific example IDs to evaluate (None = all)
            tags: Filter examples by tags (None = no filter)
            experiment_name: MLflow experiment name
        
        Returns:
            Summary dict with results
        """
        # Filter examples
        if example_ids:
            examples = [self.dataset.get_by_id(eid) for eid in example_ids]
            examples = [e for e in examples if e is not None]
        elif tags:
            examples = self.dataset.filter_by_tags(tags)
        else:
            examples = self.dataset.examples
        
        if not examples:
            logger.warning("No examples to evaluate")
            return {"total": 0, "passed": 0, "failed": 0}
        
        # Set MLflow experiment
        mlflow.set_experiment(experiment_name)
        
        # Run evaluation
        results = []
        with mlflow.start_run(run_name="eval_suite"):
            mlflow.log_param("dataset_name", self.dataset.name)
            mlflow.log_param("dataset_version", self.dataset.version)
            mlflow.log_param("num_examples", len(examples))
            
            for example in examples:
                logger.info(f"Evaluating example: {example.id}")
                
                result, scores = self.run_example(example)
                
                if result:
                    # Log metrics for this example
                    pass_rate = scores.overall_pass_rate()
                    mlflow.log_metric(f"{example.id}_pass_rate", pass_rate)
                    
                    # Log individual scores
                    for score in scores.scores:
                        mlflow.log_metric(f"{example.id}_{score.name}", score.score)
                    
                    results.append({
                        "example_id": example.id,
                        "passed": pass_rate == 1.0,
                        "pass_rate": pass_rate,
                        "scores": scores.model_dump()
                    })
                else:
                    results.append({
                        "example_id": example.id,
                        "passed": False,
                        "pass_rate": 0.0,
                        "error": "Failed to run example"
                    })
            
            # Aggregate results
            total = len(results)
            passed = sum(1 for r in results if r["passed"])
            failed = total - passed
            overall_pass_rate = passed / total if total > 0 else 0.0
            
            # Log aggregate metrics
            mlflow.log_metric("total_examples", total)
            mlflow.log_metric("passed_examples", passed)
            mlflow.log_metric("failed_examples", failed)
            mlflow.log_metric("overall_pass_rate", overall_pass_rate)
            
            # Log results as artifact
            mlflow.log_dict(
                {"results": results, "summary": {"total": total, "passed": passed, "failed": failed}},
                "eval_results.json"
            )
            
            logger.info(f"Evaluation complete: {passed}/{total} passed ({overall_pass_rate:.1%})")
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": overall_pass_rate,
            "results": results
        }


def run_eval_suite(dataset_path: Optional[Path] = None) -> dict:
    """Convenience function to run evaluation suite."""
    runner = EvalRunner(dataset_path)
    return runner.run_evaluation()
