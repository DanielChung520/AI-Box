#!/usr/bin/env bash
# RQ Worker Startup Script (Linux version)
# This script properly loads environment variables and starts the RQ worker

cd /home/daniel/ai-box

# Load environment variables from .env
export $(grep -v '^#' .env | xargs)

# Verify config path is set
if [ -z "$AI_BOX_CONFIG_PATH" ]; then
    export AI_BOX_CONFIG_PATH=/home/daniel/ai-box/config/config.json
fi

echo "Starting RQ Worker with config: $AI_BOX_CONFIG_PATH"

# Use venv Python
VENV_PYTHON=/home/daniel/ai-box/venv/bin/python
RQ_CMD=/home/daniel/ai-box/venv/bin/rq

if [ -f "$RQ_CMD" ]; then
    # Use rq command from venv
    exec $RQ_CMD worker file_processing vectorization kg_extraction agent_todo \
        --url redis://localhost:6379/0 \
        --name rq_worker_ai_box
else
    # Fall back to python -m rq
    exec $VENV_PYTHON -m rq worker file_processing vectorization kg_extraction agent_todo \
        --url redis://localhost:6379/0 \
        --name rq_worker_ai_box
fi
