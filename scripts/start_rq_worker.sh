#!/usr/bin/env bash
# RQ Worker Startup Script
# This script properly loads environment variables and starts the RQ worker

cd /Users/daniel/GitHub/AI-Box

# Load environment variables from .env
export $(grep -v '^#' .env | xargs)

# Set macOS fork safety (for Python multiprocessing)
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Verify config path is set
if [ -z "$AI_BOX_CONFIG_PATH" ]; then
    export AI_BOX_CONFIG_PATH=/Users/daniel/GitHub/AI-Box/config/config.json
fi

echo "Starting RQ Worker with config: $AI_BOX_CONFIG_PATH"

# Start the RQ worker
exec rq worker file_processing vectorization kg_extraction \
    --url redis://localhost:6379/0 \
    --name rq_worker_ai_box
