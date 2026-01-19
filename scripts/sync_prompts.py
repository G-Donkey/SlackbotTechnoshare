#!/usr/bin/env python3
"""
Script to sync YAML prompts to MLflow Prompt Registry.
Run this after updating prompt files to register new versions.
"""
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from technoshare_commentator.mlops.prompt_registry import prompt_registry
from technoshare_commentator.log import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Sync prompts to MLflow."""
    logger.info("=" * 60)
    logger.info("Syncing Prompts to MLflow Registry")
    logger.info("=" * 60)
    
    # Sync prompts
    results = prompt_registry.sync_prompts_from_yaml(force=True)
    
    # Print results
    print("\nSync Results:")
    print("-" * 60)
    for name, version in results.items():
        print(f"  {name}: {version}")
    print("-" * 60)
    print(f"\nSynced {len(results)} prompts to MLflow")
    
    logger.info("Prompt sync complete")


if __name__ == "__main__":
    main()
