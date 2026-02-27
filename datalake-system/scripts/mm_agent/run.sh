#!/bin/bash
cd /home/daniel/ai-box/datalake-system
source venv/bin/activate
exec python -c "
from mm_agent.main import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8003, log_level='info')
"
