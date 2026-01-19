#!/usr/bin/env python3
"""
Script to run the evaluation suite for TechnoShare Commentator.
Evaluates the pipeline on a curated dataset and logs results to MLflow.
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from technoshare_commentator.mlops.evaluation.runner import run_eval_suite
from technoshare_commentator.log import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Run evaluation suite."""
    logger.info("=" * 60)
    logger.info("TechnoShare Commentator - Evaluation Suite")
    logger.info("=" * 60)
    
    # Run evaluation
    results = run_eval_suite()
    
    # Print summary
    print("\n" + "=" * 60)
    print("Evaluation Results")
    print("=" * 60)
    print(f"Total examples: {results['total']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Pass rate: {results['pass_rate']:.1%}")
    print("=" * 60)
    
    # Exit with error code if any failures
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
