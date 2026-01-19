"""TechnoShare Commentator - A Slack bot that summarizes shared links using LLMs.

This package monitors a Slack channel for URLs and automatically generates
helpful summaries using a two-stage LLM pipeline (fact extraction + composition).

Components:
- main_socket: Socket Mode event listener
- main_worker: Background job processor
- pipeline: LLM processing stages
- slack: Slack API integration
- retrieval: URL content fetching
- mlops: MLflow tracking/tracing
"""
