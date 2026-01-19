#!/bin/bash

# MLflow server startup script for TechnoShare Commentator
# Starts a local MLflow tracking server with SQLite backend and local artifact storage

set -e

# Configuration
HOST="${MLFLOW_HOST:-127.0.0.1}"
PORT="${MLFLOW_PORT:-5000}"
BACKEND_STORE="${MLFLOW_BACKEND_STORE:-sqlite:///mlflow.db}"
ARTIFACT_ROOT="${MLFLOW_ARTIFACT_ROOT:-./mlartifacts}"

echo "=================================================="
echo "Starting MLflow Tracking Server"
echo "=================================================="
echo "Host: $HOST"
echo "Port: $PORT"
echo "Backend Store: $BACKEND_STORE"
echo "Artifact Root: $ARTIFACT_ROOT"
echo "=================================================="
echo ""
echo "MLflow UI will be available at: http://$HOST:$PORT"
echo ""

# Create artifact directory if it doesn't exist
mkdir -p "$ARTIFACT_ROOT"

# Start MLflow server
mlflow server \
  --host "$HOST" \
  --port "$PORT" \
  --backend-store-uri "$BACKEND_STORE" \
  --default-artifact-root "$ARTIFACT_ROOT" \
  "$@"
