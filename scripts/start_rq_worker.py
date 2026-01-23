#!/usr/bin/env python3
"""
RQ Worker Startup Script (Python version)
This script properly sets up environment and starts the RQ worker
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env
env_file = project_root / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# Set macOS fork safety
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# Set config path if not already set
if not os.environ.get("AI_BOX_CONFIG_PATH"):
    os.environ["AI_BOX_CONFIG_PATH"] = "/Users/daniel/GitHub/AI-Box/config/config.json"

print(f"Starting RQ Worker with config: {os.environ.get('AI_BOX_CONFIG_PATH')}")

from rq.worker import Worker

# Now import and run the RQ worker
from database.rq.queue import (
    FILE_PROCESSING_QUEUE,
    KG_EXTRACTION_QUEUE,
    TASK_DELETION_QUEUE,
    VECTORIZATION_QUEUE,
    get_task_queue,
)

# Create worker - include all queues
queues = [FILE_PROCESSING_QUEUE, VECTORIZATION_QUEUE, KG_EXTRACTION_QUEUE, TASK_DELETION_QUEUE]
connection = get_task_queue(FILE_PROCESSING_QUEUE).connection
worker = Worker(queues, connection=connection, name="rq_worker_ai_box")

print(f"Worker queues: {queues}")
print(f"Worker name: {worker.name}")

# Run the worker
worker.work()
