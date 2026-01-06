#!/usr/bin/env python3
# 代碼功能說明: 使用 gpt-oss:120b-cloud 模型重新生成圖譜（帶時間記錄）
# 創建日期: 2026-01-04
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-04

"""使用 gpt-oss:120b-cloud 模型重新生成圖譜（帶時間記錄）

使用方法:
    python test_regenerate_kg_gptoss.py <file_id>
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

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

# 時間記錄
time_records: List[Dict[str, any]] = []


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
    time_records.append(record)
    print(f"[{record['datetime']}] {event}")
    if details:
        for key, value in details.items():
            print(f"    {key}: {value}")


def login(username: str = "daniel@test.com", password: str = "test123") -> Optional[str]:
    """登錄獲取 access token"""
    record_time("開始登錄")
    url = f"{API_BASE}/auth/login"
    data = {"username": username, "password": password}
    
    try:
        start_time = time.time()
        response = requests.post(url, json=data, timeout=60)
        login_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                token = result.get("data", {}).get("access_token")
            else:
                token = result.get("access_token")
            
            if token:
                record_time("登錄成功", details={"耗時": f"{login_time:.3f}秒"})
                return token
            else:
                record_time("登錄失敗：無法獲取 access_token")
                return None
        else:
            record_time("登錄失敗", details={"HTTP狀態": response.status_code, "耗時": f"{login_time:.3f}秒"})
            return None
    except Exception as e:
        record_time("登錄錯誤", details={"錯誤": str(e)})
        return None


def regenerate_graph(file_id: str, token: str) -> bool:
    """重新生成圖譜"""
    record_time("開始觸發圖譜重新生成", details={"File ID": file_id, "模型": "gpt-oss:120b-cloud"})
    
    url = f"{API_BASE}/files/{file_id}/regenerate"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"type": "graph"}
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=data, timeout=30)
        request_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            record_time("圖譜重新生成已觸發", details={
                "耗時": f"{request_time:.3f}秒",
                "Job ID": result.get("data", {}).get("job_id", "N/A")
            })
            return True
        else:
            record_time("圖譜重新生成失敗", details={"HTTP狀態": response.status_code, "錯誤": response.text})
            return False
    except Exception as e:
        record_time("圖譜重新生成錯誤", details={"錯誤": str(e)})
        return False


def check_processing_status(file_id: str, token: str) -> dict:
    """檢查處理狀態"""
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


def monitor_processing(file_id: str, token: str, max_wait: int = 1200) -> bool:
    """監控處理進度（帶時間記錄）"""
    record_time("開始監控處理進度", details={"最多等待": f"{max_wait}秒", "模型": "gpt-oss:120b-cloud"})
    start_time = time.time()
    last_progress = -1
    last_status = None
    
    kg_extraction_start = None
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            record_time("監控超時", details={"已等待": f"{max_wait}秒"})
            return False
        
        status = check_processing_status(file_id, token)
        overall_status = status.get("overall_status", "unknown")
        overall_progress = status.get("overall_progress", 0)
        
        kg_extraction = status.get("kg_extraction", {})
        kg_extraction_status = kg_extraction.get("status", "unknown")
        
        # 記錄圖譜提取開始
        if kg_extraction_status == "processing" and kg_extraction_start is None:
            kg_extraction_start = time.time()
            record_time("圖譜提取階段開始（gpt-oss:120b-cloud）", details={"已用時": f"{elapsed:.2f}秒"})
        
        # 只在進度或狀態變化時打印
        if overall_progress != last_progress or overall_status != last_status:
            print(f"   進度: {overall_progress}% | 狀態: {overall_status} | 已用時: {elapsed:.0f}秒")
            last_progress = overall_progress
            last_status = overall_status
        
        if overall_status == "completed":
            total_time = time.time() - start_time
            if kg_extraction_start:
                kg_extraction_time = time.time() - kg_extraction_start
                record_time("圖譜提取階段完成（gpt-oss:120b-cloud）", details={"耗時": f"{kg_extraction_time:.2f}秒"})
            
            record_time("處理完成", details={
                "總耗時": f"{total_time:.2f}秒",
                "實體數 (NER)": kg_extraction.get("entities_count", 0),
                "關係數 (RE)": kg_extraction.get("relations_count", 0),
                "三元組數 (RT)": kg_extraction.get("triples_count", 0)
            })
            return True
        elif overall_status == "failed":
            record_time("處理失敗", details={
                "已用時": f"{elapsed:.2f}秒",
                "錯誤信息": status.get("message", "Unknown error")
            })
            return False
        
        time.sleep(5)  # 每 5 秒檢查一次


def get_kg_stats(file_id: str, token: str) -> Optional[dict]:
    """獲取圖譜統計信息"""
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


def save_time_report(file_id: str, model: str = "gpt-oss:120b-cloud"):
    """保存時間記錄報告"""
    model_safe = model.replace(":", "_").replace("-", "_")
    report_file = project_root / f"docs/測試報告_圖譜重新生成_{model_safe}_{file_id[:8]}.json"
    
    # 計算各階段耗時
    report = {
        "file_id": file_id,
        "model": model,
        "測試時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "時間記錄": time_records,
        "階段耗時統計": {}
    }
    
    # 計算各階段耗時
    events = {r["event"]: r["timestamp"] for r in time_records}
    
    if "登錄成功" in events and "開始登錄" in events:
        report["階段耗時統計"]["登錄"] = events["登錄成功"] - events.get("開始登錄", events["登錄成功"])
    
    if "圖譜重新生成已觸發" in events and "開始觸發圖譜重新生成" in events:
        report["階段耗時統計"]["觸發請求"] = events["圖譜重新生成已觸發"] - events["開始觸發圖譜重新生成"]
    
    extraction_complete_key = "圖譜提取階段完成（gpt-oss:120b-cloud）"
    extraction_start_key = "圖譜提取階段開始（gpt-oss:120b-cloud）"
    if extraction_complete_key in events and extraction_start_key in events:
        report["階段耗時統計"]["圖譜提取"] = events[extraction_complete_key] - events[extraction_start_key]
    
    if "處理完成" in events and "開始監控處理進度" in events:
        report["階段耗時統計"]["總處理時間"] = events["處理完成"] - events["開始監控處理進度"]
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 時間記錄報告已保存: {report_file}")
    return report_file


def main():
    if len(sys.argv) < 2:
        print("用法: python test_regenerate_kg_gptoss.py <file_id>")
        sys.exit(1)
    
    file_id = sys.argv[1]
    
    print("=" * 60)
    print("使用 gpt-oss:120b-cloud 模型重新生成圖譜（帶時間記錄）")
    print("=" * 60)
    print(f"File ID: {file_id}")
    print(f"模型: gpt-oss:120b-cloud (Ollama 本地)")
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 登錄
    token = login()
    if not token:
        print("❌ 無法登錄，退出")
        sys.exit(1)
    
    # 2. 觸發圖譜重新生成
    if not regenerate_graph(file_id, token):
        print("❌ 圖譜重新生成觸發失敗，退出")
        sys.exit(1)
    
    # 3. 監控處理進度
    success = monitor_processing(file_id, token, max_wait=1200)  # 20分鐘超時
    
    # 4. 獲取圖譜統計（如果處理完成）
    if success:
        record_time("開始獲取圖譜統計")
        kg_stats = get_kg_stats(file_id, token)
        if kg_stats:
            record_time("圖譜統計獲取成功", details={
                "實體總數": kg_stats.get('total_entities', 0),
                "關係總數": kg_stats.get('total_relations', 0),
                "三元組總數": kg_stats.get('total_triples', 0)
            })
    
    # 5. 保存時間記錄報告
    report_file = save_time_report(file_id, "gpt-oss:120b-cloud")
    
    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)
    print(f"File ID: {file_id}")
    print(f"模型: gpt-oss:120b-cloud")
    print(f"時間記錄報告: {report_file}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷")
        if time_records:
            report_file = save_time_report("interrupted", "gpt-oss:120b-cloud")
            print(f"已保存部分時間記錄: {report_file}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        if time_records:
            report_file = save_time_report("error", "gpt-oss:120b-cloud")
            print(f"已保存部分時間記錄: {report_file}")
        sys.exit(1)
