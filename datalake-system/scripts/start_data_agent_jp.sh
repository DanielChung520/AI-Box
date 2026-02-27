#!/bin/bash
# Data-Agent-JP 啟動腳本（設置 Oracle Client 環境）

export LD_LIBRARY_PATH=/home/daniel/instantclient_23_26:/home/daniel/oracle_libs:$LD_LIBRARY_PATH
export ORACLE_LIB_PATH=/home/daniel/instantclient_23_26

cd /home/daniel/ai-box/datalake-system
source venv/bin/activate
python3 scripts/start_data_agent_jp_service.py
