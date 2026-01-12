#!/usr/bin/env python3
# 代碼功能說明: 測試文件上傳、向量化和圖譜提取（帶時間記錄）
# 創建日期: 2026-01-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-03

"""測試文件上傳、向量化和圖譜提取（帶詳細時間記錄）

使用方法:
    python test_upload_生质能源_带时间记录.py
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

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
        "details": details or {},
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
                record_time(
                    "登錄成功", details={"耗時": f"{login_time:.3f}秒", "HTTP狀態": response.status_code}
                )
                return token
            else:
                record_time("登錄失敗：無法獲取 access_token", details={"響應": result})
                return None
        else:
            record_time(
                "登錄失敗",
                details={
                    "HTTP狀態": response.status_code,
                    "錯誤": response.text,
                    "耗時": f"{login_time:.3f}秒",
                },
            )
            return None
    except Exception as e:
        record_time("登錄錯誤", details={"錯誤": str(e)})
        return None


def upload_file(file_path: Path, token: str, task_id: Optional[str] = None) -> Optional[dict]:
    """上傳文件"""
    record_time(
        "開始上傳文件",
        details={"文件名": file_path.name, "文件大小": f"{file_path.stat().st_size / 1024 / 1024:.2f} MB"},
    )

    url = f"{API_BASE}/files/upload"
    headers = {"Authorization": f"Bearer {token}"}

    # 準備 multipart/form-data
    with open(file_path, "rb") as f:
        files = {"files": (file_path.name, f, "application/pdf")}
        data = {}
        if task_id:
            data["task_id"] = task_id

        try:
            upload_start = time.time()
            response = requests.post(url, headers=headers, files=files, data=data, timeout=300)
            upload_time = time.time() - upload_start

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    uploaded = result.get("data", {}).get("uploaded", [])
                    if uploaded:
                        file_info = uploaded[0]
                        record_time(
                            "文件上傳成功",
                            details={
                                "耗時": f"{upload_time:.3f}秒",
                                "File ID": file_info.get("file_id"),
                                "文件名": file_info.get("filename"),
                                "文件類型": file_info.get("file_type"),
                                "文件大小": f"{file_info.get('file_size', 0) / 1024 / 1024:.2f} MB",
                            },
                        )
                        return file_info
                else:
                    record_time(
                        "文件上傳失敗",
                        details={
                            "錯誤": result.get("message", "Unknown error"),
                            "耗時": f"{upload_time:.3f}秒",
                        },
                    )
                    return None
            else:
                record_time(
                    "文件上傳失敗",
                    details={
                        "HTTP狀態": response.status_code,
                        "錯誤": response.text,
                        "耗時": f"{upload_time:.3f}秒",
                    },
                )
                return None
        except Exception as e:
            record_time("文件上傳錯誤", details={"錯誤": str(e)})
            import traceback

            traceback.print_exc()
            return None


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
    except Exception:
        return {}


def monitor_processing(file_id: str, token: str, max_wait: int = 600) -> bool:
    """監控處理進度（帶時間記錄）"""
    record_time("開始監控處理進度", details={"最多等待": f"{max_wait}秒"})
    start_time = time.time()
    last_progress = -1
    last_status = None

    # 記錄各階段開始時間
    chunking_start = None
    vectorization_start = None
    storage_start = None
    kg_extraction_start = None

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            record_time("監控超時", details={"已等待": f"{max_wait}秒"})
            return False

        status = check_processing_status(file_id, token)
        overall_status = status.get("overall_status", "unknown")
        overall_progress = status.get("overall_progress", 0)

        # 檢查各階段狀態
        chunking = status.get("chunking", {})
        vectorization = status.get("vectorization", {})
        storage = status.get("storage", {})
        kg_extraction = status.get("kg_extraction", {})

        chunking_status = chunking.get("status", "unknown")
        vectorization_status = vectorization.get("status", "unknown")
        storage_status = storage.get("status", "unknown")
        kg_extraction_status = kg_extraction.get("status", "unknown")

        # 記錄階段開始
        if chunking_status == "processing" and chunking_start is None:
            chunking_start = time.time()
            record_time("分塊階段開始", details={"已用時": f"{elapsed:.2f}秒"})

        if vectorization_status == "processing" and vectorization_start is None:
            vectorization_start = time.time()
            if chunking_start:
                chunking_time = time.time() - chunking_start
                record_time(
                    "分塊階段完成",
                    details={"耗時": f"{chunking_time:.2f}秒", "分塊數": chunking.get("chunk_count", 0)},
                )
            record_time("向量化階段開始", details={"已用時": f"{elapsed:.2f}秒"})

        if storage_status == "processing" and storage_start is None:
            storage_start = time.time()
            if vectorization_start:
                vectorization_time = time.time() - vectorization_start
                record_time("向量化階段完成", details={"耗時": f"{vectorization_time:.2f}秒"})
            record_time("存儲階段開始", details={"已用時": f"{elapsed:.2f}秒"})

        if kg_extraction_status == "processing" and kg_extraction_start is None:
            kg_extraction_start = time.time()
            if storage_start:
                storage_time = time.time() - storage_start
                record_time(
                    "存儲階段完成",
                    details={"耗時": f"{storage_time:.2f}秒", "向量數": storage.get("vector_count", 0)},
                )
            record_time("圖譜提取階段開始", details={"已用時": f"{elapsed:.2f}秒"})

        # 只在進度或狀態變化時打印
        if overall_progress != last_progress or overall_status != last_status:
            print(f"   進度: {overall_progress}% | 狀態: {overall_status} | 已用時: {elapsed:.0f}秒")
            last_progress = overall_progress
            last_status = overall_status

        if overall_status == "completed":
            total_time = time.time() - start_time
            if kg_extraction_start:
                kg_extraction_time = time.time() - kg_extraction_start
                record_time("圖譜提取階段完成", details={"耗時": f"{kg_extraction_time:.2f}秒"})

            record_time(
                "處理完成",
                details={
                    "總耗時": f"{total_time:.2f}秒",
                    "分塊數": chunking.get("chunk_count", 0),
                    "向量數": storage.get("vector_count", 0),
                    "實體數 (NER)": kg_extraction.get("entities_count", 0),
                    "關係數 (RE)": kg_extraction.get("relations_count", 0),
                    "三元組數 (RT)": kg_extraction.get("triples_count", 0),
                },
            )
            return True
        elif overall_status == "failed":
            record_time(
                "處理失敗",
                details={"已用時": f"{elapsed:.2f}秒", "錯誤信息": status.get("message", "Unknown error")},
            )
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
    except Exception:
        return None


def save_time_report(file_id: str):
    """保存時間記錄報告"""
    report_file = project_root / f"docs/測試報告_生质能源-Daniel笔记_時間記錄_{file_id[:8]}.json"

    # 計算各階段耗時
    report = {
        "file_id": file_id,
        "測試時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "時間記錄": time_records,
        "階段耗時統計": {},
    }

    # 計算各階段耗時
    events = {r["event"]: r["timestamp"] for r in time_records}

    if "登錄成功" in events and "開始上傳文件" in events:
        report["階段耗時統計"]["登錄"] = events["登錄成功"] - events.get("開始登錄", events["登錄成功"])

    if "文件上傳成功" in events and "開始上傳文件" in events:
        report["階段耗時統計"]["文件上傳"] = events["文件上傳成功"] - events["開始上傳文件"]

    if "分塊階段完成" in events and "分塊階段開始" in events:
        report["階段耗時統計"]["分塊"] = events["分塊階段完成"] - events["分塊階段開始"]

    if "向量化階段完成" in events and "向量化階段開始" in events:
        report["階段耗時統計"]["向量化"] = events["向量化階段完成"] - events["向量化階段開始"]

    if "存儲階段完成" in events and "存儲階段開始" in events:
        report["階段耗時統計"]["存儲"] = events["存儲階段完成"] - events["存儲階段開始"]

    if "圖譜提取階段完成" in events and "圖譜提取階段開始" in events:
        report["階段耗時統計"]["圖譜提取"] = events["圖譜提取階段完成"] - events["圖譜提取階段開始"]

    if "處理完成" in events and "開始監控處理進度" in events:
        report["階段耗時統計"]["總處理時間"] = events["處理完成"] - events["開始監控處理進度"]

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📊 時間記錄報告已保存: {report_file}")
    return report_file


def main():
    file_path = Path("docs/生质能源-Daniel笔记.pdf")
    task_id = None

    if not file_path.exists():
        print(f"❌ 錯誤：文件不存在: {file_path}")
        sys.exit(1)

    print("=" * 60)
    print("文件上傳、向量化和圖譜提取測試（帶時間記錄）")
    print("=" * 60)
    print(f"測試文件: {file_path.name}")
    print(f"文件大小: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 登錄
    token = login()
    if not token:
        print("❌ 無法登錄，退出")
        sys.exit(1)

    # 2. 上傳文件
    file_info = upload_file(file_path, token, task_id)
    if not file_info:
        print("❌ 文件上傳失敗，退出")
        sys.exit(1)

    file_id = file_info.get("file_id")
    if not file_id:
        print("❌ 無法獲取 File ID，退出")
        sys.exit(1)

    # 3. 監控處理進度
    success = monitor_processing(file_id, token, max_wait=600)

    # 4. 獲取圖譜統計（如果處理完成）
    if success:
        record_time("開始獲取圖譜統計")
        kg_stats = get_kg_stats(file_id, token)
        if kg_stats:
            record_time(
                "圖譜統計獲取成功",
                details={
                    "實體總數": kg_stats.get("total_entities", 0),
                    "關係總數": kg_stats.get("total_relations", 0),
                    "三元組總數": kg_stats.get("total_triples", 0),
                },
            )

    # 5. 保存時間記錄報告
    report_file = save_time_report(file_id)

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)
    print(f"File ID: {file_id}")
    if task_id:
        print(f"Task ID: {task_id}")
    print(f"時間記錄報告: {report_file}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用戶中斷")
        # 保存已記錄的時間
        if time_records:
            report_file = save_time_report("interrupted")
            print(f"已保存部分時間記錄: {report_file}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback

        traceback.print_exc()
        # 保存已記錄的時間
        if time_records:
            report_file = save_time_report("error")
            print(f"已保存部分時間記錄: {report_file}")
        sys.exit(1)
