#!/usr/bin/env python3
# 代碼功能說明: 參數使用位置檢核腳本
# 創建日期: 2026-01-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-01

"""掃描代碼中所有環境變量的使用位置，生成參數檢核報告"""

import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set

def scan_env_vars(project_root: Path) -> Dict[str, Set[str]]:
    """掃描代碼中所有環境變量的使用位置"""
    param_usage: Dict[str, Set[str]] = defaultdict(set)
    
    for py_file in project_root.rglob('*.py'):
        # 排除第三方庫和測試文件
        if any(x in str(py_file) for x in ['venv', 'node_modules', '.git', '__pycache__', 'backup', 'tests']):
            continue
        try:
            content = py_file.read_text(encoding='utf-8')
            rel_path = str(py_file.relative_to(project_root))
            
            # 匹配 os.getenv("VAR_NAME") 或 os.environ.get("VAR_NAME")
            for match in re.finditer(r'os\.getenv\(["\']([^"\']+)["\']', content):
                param = match.group(1)
                if param and not param.startswith('_') and not param.startswith('TEST_') and not param.startswith('SMOKE_') and not param.startswith('SKIP_'):
                    param_usage[param].add(rel_path)
        except Exception:
            pass
    
    return param_usage

def main():
    project_root = Path(__file__).parent.parent
    param_usage = scan_env_vars(project_root)
    
    print(f"找到 {len(param_usage)} 個不同的環境變量\n")
    
    # 按類別組織輸出
    categories = {
        'API服務': ['API_GATEWAY_HOST', 'API_GATEWAY_PORT', 'ENV', 'CORS_ORIGINS'],
        'ArangoDB': ['ARANGODB_HOST', 'ARANGODB_PORT', 'ARANGODB_USERNAME', 'ARANGODB_PASSWORD', 'ARANGODB_DATABASE', 'ARANGODB_PROTOCOL'],
        'Redis': ['REDIS_HOST', 'REDIS_PORT', 'REDIS_DB', 'REDIS_URL', 'REDIS_PASSWORD'],
        'ChromaDB': ['CHROMADB_HOST', 'CHROMADB_PORT', 'CHROMADB_MODE', 'CHROMADB_PERSIST_DIR', 'CHROMADB_CONNECTION_POOL_SIZE', 'CHROMADB_NAMESPACE'],
        'Ollama': ['OLLAMA_BASE_URL', 'OLLAMA_SCHEME', 'OLLAMA_REMOTE_HOST', 'OLLAMA_REMOTE_PORT', 'OLLAMA_TIMEOUT_SECONDS', 'OLLAMA_DEFAULT_MODEL', 'OLLAMA_EMBEDDING_MODEL', 'OLLAMA_NER_MODEL', 'OLLAMA_RE_MODEL', 'OLLAMA_RT_MODEL', 'OLLAMA_API_TOKEN', 'OLLAMA_URL'],
        'SeaweedFS': ['AI_BOX_SEAWEEDFS_S3_ENDPOINT', 'AI_BOX_SEAWEEDFS_S3_ACCESS_KEY', 'AI_BOX_SEAWEEDFS_S3_SECRET_KEY', 'AI_BOX_SEAWEEDFS_USE_SSL', 'AI_BOX_SEAWEEDFS_FILER_ENDPOINT', 'DATALAKE_SEAWEEDFS_S3_ENDPOINT', 'DATALAKE_SEAWEEDFS_S3_ACCESS_KEY', 'DATALAKE_SEAWEEDFS_S3_SECRET_KEY', 'DATALAKE_SEAWEEDFS_USE_SSL', 'DATALAKE_SEAWEEDFS_FILER_ENDPOINT'],
        '安全': ['JWT_SECRET_KEY', 'GENAI_SECRET_ENCRYPTION_KEY', 'FILE_ENCRYPTION_KEY', 'SECURITY_ENABLED', 'SECURITY_MODE'],
        'Agent': ['AGENT_HEARTBEAT_TIMEOUT', 'AGENT_HEALTH_CHECK_INTERVAL', 'AGENT_SECRET_ID', 'AGENT_SECRET_KEY'],
        'MCP': ['MCP_SERVER_ENDPOINTS', 'MCP_SERVER_HOST', 'MCP_SERVER_PORT'],
        '嵌入服務': ['EMBEDDING_BATCH_SIZE'],
        '日誌': ['LOG_LEVEL', 'LOG_MAX_SIZE'],
    }
    
    all_params = set()
    for params in categories.values():
        all_params.update(params)
    
    print("=" * 80)
    print("參數使用位置檢核報告")
    print("=" * 80)
    
    for category, params in categories.items():
        print(f"\n【{category}】")
        for param in sorted(params):
            if param in param_usage:
                files = sorted(param_usage[param])
                print(f"  ✅ {param} ({len(files)} 個文件)")
                for f in files[:3]:
                    print(f"     - {f}")
                if len(files) > 3:
                    print(f"     ... 還有 {len(files) - 3} 個文件")
            else:
                print(f"  ⚠️  {param} (代碼中未找到使用)")
    
    # 列出未分類的參數
    uncategorized = set(param_usage.keys()) - all_params
    if uncategorized:
        print(f"\n【未分類參數】({len(uncategorized)} 個)")
        for param in sorted(uncategorized):
            files = sorted(param_usage[param])
            print(f"  ⚠️  {param} ({len(files)} 個文件)")

if __name__ == '__main__':
    main()
