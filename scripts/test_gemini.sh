#!/bin/bash
# 配置Gemini模型并运行测试

export NER_MODEL_TYPE=gemini
export RE_MODEL_TYPE=gemini
export RT_MODEL_TYPE=gemini
export OLLAMA_NER_MODEL=gemini-pro
export OLLAMA_RE_MODEL=gemini-pro
export OLLAMA_RT_MODEL=gemini-pro

echo "配置Gemini模型环境变量..."
echo "NER_MODEL_TYPE=$NER_MODEL_TYPE"
echo "RE_MODEL_TYPE=$RE_MODEL_TYPE"
echo "RT_MODEL_TYPE=$RT_MODEL_TYPE"

python3 scripts/kg_extract_test_file.py \
  --file "docs/系统设计文档/统一服务指南.md" \
  --model gemini \
  --user-id "test-user" \
  --output "test_results_gemini.json"
