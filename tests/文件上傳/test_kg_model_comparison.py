#!/usr/bin/env python3
# 代碼功能說明: 圖譜模型對比測試（系統測試框架）
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""圖譜模型對比測試（系統測試框架）

測試目標：
1. 驗證系統正確性
2. 不同模型的效能對比
3. 圖譜生成質量評估

使用方法:
    python test_kg_model_comparison.py <file_id> <model_name>
    
範例:
    # 測試 mistral-nemo:12b（基準模型）
    python test_kg_model_comparison.py 149aee1a-89da-4b07-a83c-634fb29246e2 mistral-nemo:12b
    
    # 測試 gpt-oss:120b-cloud
    python test_kg_model_comparison.py 149aee1a-89da-4b07-a83c-634fb29246e2 gpt-oss:120b-cloud
    
    # 測試 qwen3-next:latest
    python test_kg_model_comparison.py 149aee1a-89da-4b07-a83c-634fb29246e2 qwen3-next:latest
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

import requests
from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加載環境變數
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

API_BASE = "http://localhost:8000/api/v1"

# 測試結果記錄
test_results: Dict[str, Any] = {
    "file_id": "",
    "test_time": "",
    "model_name": "",
    "time_records": [],
    "config_info": {},
    "kg_stats": {},
    "processing_status": {},
    "summary": {}
}


def record_time(event: str, timestamp: Optional[float] = None, details: Optional[Dict] = None):
    """記錄時間點"""
    if timestamp is None:
        timestamp = time.time()
    
    record = {
        "event": event,
        "timestamp": timestamp,
        "datetime": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "details": details or {}
    }
    test_results["time_records"].append(record)
    print(f"[{record['datetime']}] {event}")
    if details:
        for key, value in details.items():
            print(f"    {key}: {value}")


def login(username: str = "daniel@test.com", password: str = "test123") -> Optional[str]:
    """登錄獲取 access token（調用系統 API）"""
    record_time("開始登錄")
    url = f"{API_BASE}/auth/login"
    data = {"username": username, "password": password}
    
    try:
        start_time = time.time()
        response = requests.post(url, json=data, timeout=60)
        login_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            token = result.get("data", {}).get("access_token") or result.get("access_token")
            
            if token:
                record_time("登錄成功", details={"耗時": f"{login_time:.3f}秒"})
                return token
            else:
                record_time("登錄失敗：無法獲取 access_token")
                return None
        else:
            record_time("登錄失敗", details={"HTTP狀態": response.status_code})
            return None
    except Exception as e:
        record_time("登錄錯誤", details={"錯誤": str(e)})
        return None


def verify_model_config(token: str, expected_model: str) -> Dict[str, Any]:
    """驗證系統實際使用的模型配置（查詢 ArangoDB 配置）"""
    record_time("開始驗證模型配置", details={"預期模型": expected_model})
    
    config_info = {
        "expected_model": expected_model,
        "verified": False,
        "arango_config": {},
        "note": ""
    }
    
    try:
        # 直接查詢 ArangoDB 配置（使用系統服務）
        from services.api.services.config_store_service import ConfigStoreService
        
        service = ConfigStoreService()
        kg_config = service.get_config("kg_extraction", tenant_id=None)
        
        if kg_config and kg_config.config_data:
            config_data = kg_config.config_data
            arango_config = {
                "ner_model_type": config_data.get("ner_model_type"),
                "ner_model": config_data.get("ner_model"),
                "re_model_type": config_data.get("re_model_type"),
                "re_model": config_data.get("re_model"),
                "rt_model_type": config_data.get("rt_model_type"),
                "rt_model": config_data.get("rt_model"),
            }
            
            config_info["arango_config"] = arango_config
            
            # 驗證配置是否匹配預期模型
            actual_ner = arango_config.get("ner_model")
            actual_re = arango_config.get("re_model")
            actual_rt = arango_config.get("rt_model")
            
            if actual_ner == expected_model and actual_re == expected_model and actual_rt == expected_model:
                config_info["verified"] = True
                config_info["note"] = "✅ ArangoDB 配置與預期模型一致"
                record_time("配置驗證成功", details={
                    "ArangoDB 配置": arango_config,
                    "驗證結果": "一致"
                })
            else:
                config_info["verified"] = False
                config_info["note"] = f"⚠️ ArangoDB 配置與預期模型不一致（NER: {actual_ner}, RE: {actual_re}, RT: {actual_rt}）"
                record_time("配置驗證失敗", details={
                    "ArangoDB 配置": arango_config,
                    "預期模型": expected_model,
                    "驗證結果": "不一致"
                })
        else:
            config_info["note"] = "⚠️ 未找到 ArangoDB kg_extraction 配置"
            record_time("配置驗證失敗", details={"原因": "未找到配置"})
            
    except ImportError as e:
        config_info["note"] = f"⚠️ 無法導入 ConfigStoreService: {e}"
        record_time("配置驗證失敗", details={"錯誤": str(e)})
    except Exception as e:
        config_info["note"] = f"⚠️ 查詢 ArangoDB 配置時發生錯誤: {e}"
        record_time("配置驗證錯誤", details={"錯誤": str(e)})
    
    test_results["config_info"] = config_info
    return config_info


def regenerate_graph(file_id: str, token: str, model_name: str) -> bool:
    """重新生成圖譜（調用系統 API）"""
    record_time("開始觸發圖譜重新生成", details={"File ID": file_id, "模型": model_name})
    
    url = f"{API_BASE}/files/{file_id}/regenerate"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"type": "graph"}
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=data, timeout=30)
        request_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                record_time("圖譜重新生成請求成功", details={"耗時": f"{request_time:.3f}秒"})
                return True
            else:
                record_time("圖譜重新生成請求失敗", details={"錯誤": result.get("message")})
                return False
        else:
            record_time("圖譜重新生成請求失敗", details={"HTTP狀態": response.status_code, "響應": response.text})
            return False
    except Exception as e:
        record_time("圖譜重新生成請求錯誤", details={"錯誤": str(e)})
        return False


def check_processing_status(file_id: str, token: str) -> Dict[str, Any]:
    """檢查處理狀態（調用系統 API）"""
    url = f"{API_BASE}/files/{file_id}/processing-status"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", {})
        else:
            return {}
    except Exception as e:
        return {}


def monitor_processing(file_id: str, token: str, max_wait: int = 300) -> bool:
    """監控處理進度（調用系統狀態管理 API）"""
    record_time("開始監控處理進度", details={"最大等待時間": f"{max_wait}秒"})
    
    start_time = time.time()
    last_progress = -1
    last_status = ""
    
    while time.time() - start_time < max_wait:
        status = check_processing_status(file_id, token)
        if not status:
            time.sleep(5)
            continue
        
        # API 返回的字段是 status 和 progress，不是 overall_status 和 overall_progress
        overall_status = status.get("status") or status.get("overall_status", "")
        overall_progress = status.get("progress") or status.get("overall_progress", 0)
        kg_extraction = status.get("kg_extraction", {})
        
        # 記錄狀態變化
        if overall_progress != last_progress or overall_status != last_status:
            record_time("處理狀態更新", details={
                "狀態": overall_status,
                "進度": f"{overall_progress}%",
                "已用時": f"{time.time() - start_time:.1f}秒"
            })
            last_progress = overall_progress
            last_status = overall_status
        
        if overall_status == "completed":
            total_time = time.time() - start_time
            test_results["processing_status"] = status
            
            # 記錄圖譜統計
            entities_count = kg_extraction.get("entities_count", 0)
            relations_count = kg_extraction.get("relations_count", 0)
            triples_count = kg_extraction.get("triples_count", 0)
            
            record_time("處理完成", details={
                "總耗時": f"{total_time:.2f}秒",
                "實體數 (NER)": entities_count,
                "關係數 (RE)": relations_count,
                "三元組數 (RT)": triples_count
            })
            
            test_results["summary"] = {
                "total_time": total_time,
                "entities_count": entities_count,
                "relations_count": relations_count,
                "triples_count": triples_count,
                "status": "completed"
            }
            
            return True
        elif overall_status == "failed":
            record_time("處理失敗", details={
                "錯誤信息": status.get("message", "Unknown error")
            })
            test_results["summary"]["status"] = "failed"
            return False
        
        time.sleep(5)
    
    record_time("監控超時", details={"已用時": f"{max_wait}秒"})
    test_results["summary"]["status"] = "timeout"
    return False


def get_kg_stats(file_id: str, token: str) -> Optional[Dict[str, Any]]:
    """獲取圖譜統計信息（調用系統 API）"""
    url = f"{API_BASE}/files/{file_id}/kg/stats"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get("data", {})
        else:
            return None
    except Exception as e:
        return None


def save_test_report(file_id: str, model_name: str):
    """保存測試報告"""
    # 生成報告文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model_name = model_name.replace(":", "_").replace("/", "_")
    report_file = project_root / f"docs/測試報告_模型對比_{safe_model_name}_{file_id[:8]}_{timestamp}.json"
    
    # 確保目錄存在
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存 JSON 報告
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 測試報告已保存: {report_file}")
    
    # 生成 Markdown 摘要
    md_file = report_file.with_suffix(".md")
    generate_markdown_report(md_file)
    
    return report_file


def generate_markdown_report(md_file: Path):
    """生成 Markdown 格式的測試報告摘要"""
    summary = test_results["summary"]
    config_info = test_results["config_info"]
    
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# 圖譜模型對比測試報告\n\n")
        f.write(f"**測試時間**: {test_results['test_time']}\n")
        f.write(f"**文件 ID**: {test_results['file_id']}\n")
        f.write(f"**測試模型**: {test_results['model_name']}\n\n")
        
        f.write("## 配置信息\n\n")
        f.write(f"- **預期模型**: {config_info.get('expected_model', 'N/A')}\n")
        f.write(f"- **配置驗證**: {'✅ 通過' if config_info.get('verified') else '⚠️ 未驗證'}\n")
        
        arango_config = config_info.get('arango_config', {})
        if arango_config:
            f.write(f"- **ArangoDB 配置**:\n")
            f.write(f"  - NER: {arango_config.get('ner_model_type', 'N/A')} - {arango_config.get('ner_model', 'N/A')}\n")
            f.write(f"  - RE: {arango_config.get('re_model_type', 'N/A')} - {arango_config.get('re_model', 'N/A')}\n")
            f.write(f"  - RT: {arango_config.get('rt_model_type', 'N/A')} - {arango_config.get('rt_model', 'N/A')}\n")
        
        note = config_info.get('note', '')
        if note:
            f.write(f"- **備註**: {note}\n")
        f.write("\n")
        
        f.write("## 測試結果摘要\n\n")
        if summary.get("status") == "completed":
            f.write(f"- **狀態**: ✅ 成功完成\n")
            f.write(f"- **總耗時**: {summary.get('total_time', 0):.2f} 秒\n")
            f.write(f"- **實體數 (NER)**: {summary.get('entities_count', 0)}\n")
            f.write(f"- **關係數 (RE)**: {summary.get('relations_count', 0)}\n")
            f.write(f"- **三元組數 (RT)**: {summary.get('triples_count', 0)}\n")
        else:
            f.write(f"- **狀態**: ❌ {summary.get('status', 'unknown')}\n")
        
        f.write("\n## 時間記錄\n\n")
        f.write("| 時間 | 事件 | 詳情 |\n")
        f.write("|------|------|------|\n")
        for record in test_results["time_records"]:
            details_str = ", ".join([f"{k}={v}" for k, v in (record.get("details") or {}).items()])
            f.write(f"| {record['datetime']} | {record['event']} | {details_str} |\n")
    
    print(f"📝 Markdown 報告已保存: {md_file}")


def main():
    if len(sys.argv) < 3:
        print("使用方法: python test_kg_model_comparison.py <file_id> <model_name>")
        print("範例: python test_kg_model_comparison.py 149aee1a-89da-4b07-a83c-634fb29246e2 mistral-nemo:12b")
        sys.exit(1)
    
    file_id = sys.argv[1]
    model_name = sys.argv[2]
    
    test_results["file_id"] = file_id
    test_results["model_name"] = model_name
    test_results["test_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"🚀 開始圖譜模型對比測試")
    print(f"文件 ID: {file_id}")
    print(f"測試模型: {model_name}")
    print(f"=" * 60)
    
    # 1. 登錄
    token = login()
    if not token:
        print("❌ 登錄失敗，測試終止")
        sys.exit(1)
    
    # 2. 驗證配置（可選）
    verify_model_config(token, model_name)
    
    # 3. 觸發圖譜重新生成
    if not regenerate_graph(file_id, token, model_name):
        print("❌ 圖譜重新生成請求失敗，測試終止")
        sys.exit(1)
    
    # 4. 監控處理進度
    if not monitor_processing(file_id, token):
        print("❌ 圖譜生成失敗或超時")
        sys.exit(1)
    
    # 5. 獲取圖譜統計
    kg_stats = get_kg_stats(file_id, token)
    if kg_stats:
        test_results["kg_stats"] = kg_stats
        record_time("獲取圖譜統計成功", details=kg_stats)
    
    # 6. 保存測試報告
    save_test_report(file_id, model_name)
    
    print(f"\n✅ 測試完成")
    print(f"=" * 60)
    summary = test_results["summary"]
    if summary.get("status") == "completed":
        print(f"總耗時: {summary.get('total_time', 0):.2f} 秒")
        print(f"實體數 (NER): {summary.get('entities_count', 0)}")
        print(f"關係數 (RE): {summary.get('relations_count', 0)}")
        print(f"三元組數 (RT): {summary.get('triples_count', 0)}")


if __name__ == "__main__":
    main()

