#!/usr/bin/env python3
# 代碼功能說明: 批量處理系統設計文檔並記錄詳細進度（重新創建版本）
# 創建日期: 2026-01-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-01

"""批量處理系統設計文檔並記錄詳細進度表

使用方法:
    python scripts/kg_extract_all_with_progress.py
    
    # 後台運行
    nohup python scripts/kg_extract_all_with_progress.py > logs/kg_extract_$(date +%Y%m%d_%H%M%S).log 2>&1 &
    
    # 監控進度
    python scripts/monitor_kg_extract.py
"""

import json
import sys
import time
import requests
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# 加載環境變數
load_dotenv(project_root / ".env")

# API 配置
API_BASE_URL = "http://localhost:8000/api/v1"
API_USERNAME = "test"
API_PASSWORD = "test"

# 文檔目錄
DOCS_DIR = project_root / "docs/系统设计文档"

# 進度表文件
PROGRESS_FILE = project_root / "scripts/kg_extract_progress.json"

# 全局變數：用於優雅退出
_should_stop = False


def signal_handler(signum, frame):
    """信號處理器：處理 Ctrl+C 和終止信號"""
    global _should_stop
    print("\n⚠️  收到終止信號，正在優雅退出...")
    _should_stop = True


# 註冊信號處理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_worker_job_timeout() -> int:
    """動態獲取 worker.job_timeout 配置"""
    try:
        from services.api.services.config_store_service import ConfigStoreService
        config_service = ConfigStoreService()
        config = config_service.get_config("worker", tenant_id=None)
        if config and config.config_data:
            timeout = config.config_data.get("job_timeout", 900)
            print(f"✅ 使用 worker.job_timeout: {timeout} 秒")
            return int(timeout)
    except Exception as e:
        print(f"⚠️  無法讀取 worker.job_timeout，使用默認值 900 秒: {e}")
    
    return 900  # 默認 900 秒（15分鐘）


class ProcessingProgressTracker:
    """處理進度追蹤器"""
    
    def __init__(self, progress_file: Path):
        self.progress_file = progress_file
        self.progress_data = self._load_progress()
    
    def _load_progress(self) -> Dict[str, Any]:
        """加載進度數據"""
        default_data = {
            "created_at": datetime.now().isoformat(),
            "files": {},
            "summary": {
                "total_files": 0,
                "processed_files": 0,
                "failed_files": 0,
                "total_entities": 0,
                "total_relations": 0,
                "total_processing_time": 0.0,
            }
        }
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if "files" not in data:
                        data["files"] = {}
                    if "summary" not in data:
                        data["summary"] = default_data["summary"]
                    return data
            except Exception as e:
                print(f"⚠️  加載進度文件失敗: {e}")
        return default_data
    
    def save_progress(self):
        """保存進度數據"""
        self.progress_data["updated_at"] = datetime.now().isoformat()
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  保存進度文件失敗: {e}")
    
    def add_file_record(self, filename: str, file_id: str, file_size: int):
        """添加文件記錄"""
        self.progress_data["files"][filename] = {
            "file_id": file_id,
            "file_size": file_size,
            "status": "processing",
            "uploaded_at": datetime.now().isoformat(),
        }
        self.save_progress()
    
    def update_file_status(self, filename: str, status: str, error: Optional[str] = None, **kwargs):
        """更新文件狀態"""
        if filename not in self.progress_data["files"]:
            self.progress_data["files"][filename] = {}
        
        self.progress_data["files"][filename].update({
            "status": status,
            "updated_at": datetime.now().isoformat(),
            **kwargs
        })
        
        if error:
            self.progress_data["files"][filename]["error"] = error
        
        if status == "completed":
            self.progress_data["summary"]["processed_files"] = (
                self.progress_data["summary"].get("processed_files", 0) + 1
            )
        elif status == "failed":
            self.progress_data["summary"]["failed_files"] = (
                self.progress_data["summary"].get("failed_files", 0) + 1
            )
        
        self.save_progress()


def login() -> Optional[str]:
    """登入獲取 token"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": API_USERNAME, "password": API_PASSWORD},
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("data", {}).get("access_token")
            if token:
                print("✅ 登入成功")
                return token
        print(f"❌ 登入失敗: {response.status_code} - {response.text}")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ 無法連接到 API 服務器，請確認 API 服務正在運行")
        return None
    except Exception as e:
        print(f"❌ 登入錯誤: {e}")
        return None


def upload_file(file_path: Path, token: str) -> Optional[str]:
    """上傳文件"""
    try:
        with open(file_path, 'rb') as f:
            files = {'files': (file_path.name, f, 'text/markdown')}
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.post(
                f"{API_BASE_URL}/files/upload",
                files=files,
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                uploaded_files = data.get("data", {}).get("uploaded", [])
                if uploaded_files:
                    file_id = uploaded_files[0].get("file_id")
                    print(f"  ✅ 文件上傳成功: {file_id}")
                    return file_id
        print(f"  ❌ 文件上傳失敗: {response.status_code} - {response.text[:200]}")
        return None
    except Exception as e:
        print(f"  ❌ 文件上傳錯誤: {e}")
        return None


def wait_for_processing(file_id: str, token: str, timeout: int) -> Dict[str, Any]:
    """等待處理完成，返回詳細時間信息"""
    start_time = time.time()
    headers = {'Authorization': f'Bearer {token}'}
    
    print(f"  ⏳ 等待處理完成（超時: {timeout} 秒）...")
    
    while time.time() - start_time < timeout:
        if _should_stop:
            return {
                "status": "cancelled",
                "error": "用戶中斷",
                "total_time": time.time() - start_time
            }
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/files/{file_id}/processing-status",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                time.sleep(3)
                continue
            
            data = response.json()
            if not data.get("success"):
                time.sleep(3)
                continue
            
            status_data = data.get("data", {})
            overall_status = status_data.get("overall_status", "")
            overall_progress = status_data.get("overall_progress", 0)
            kg_status = status_data.get("kg_extraction", {})
            kg_status_value = kg_status.get("status", "")
            kg_progress = kg_status.get("progress", 0)
            
            elapsed = int(time.time() - start_time)
            print(f"  ⏱️  [{elapsed}s] 整體進度: {overall_progress}%, KG提取: {kg_progress}% ({kg_status_value})")
            
            if overall_status == "completed":
                total_time = time.time() - start_time
                print(f"  ✅ 處理完成！總耗時: {total_time:.1f} 秒")
                return {
                    "status": "completed",
                    "total_time": total_time,
                    "final_status": status_data,
                }
            elif overall_status == "failed":
                error_msg = status_data.get("error", "Unknown error")
                print(f"  ❌ 處理失敗: {error_msg}")
                return {
                    "status": "failed",
                    "error": error_msg,
                    "total_time": time.time() - start_time
                }
            
            time.sleep(3)
        except Exception as e:
            print(f"  ⚠️  獲取狀態錯誤: {e}")
            time.sleep(3)
    
    # 超時
    error_msg = f"處理超時（超過 {timeout} 秒）"
    print(f"  ⏱️  {error_msg}")
    return {
        "status": "timeout",
        "error": error_msg,
        "total_time": timeout
    }


def get_kg_results(file_id: str, token: str) -> Dict[str, Any]:
    """獲取知識圖譜提取結果"""
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(
            f"{API_BASE_URL}/files/{file_id}/kg",
            headers=headers,
            timeout=30
        )
        if response.status_code == 200:
            return response.json().get("data", {})
        return {}
    except Exception as e:
        print(f"  ⚠️  獲取 KG 結果錯誤: {e}")
        return {}


def main():
    """主函數"""
    print("=" * 80)
    print("🚀 批量處理系統設計文檔（重新創建版本）")
    print("=" * 80)
    
    # 獲取動態超時配置
    worker_timeout = get_worker_job_timeout()
    wait_timeout = worker_timeout + 60  # 等待超時 = worker_timeout + 60 秒緩衝
    
    print(f"\n📋 配置:")
    print(f"  - Worker Job Timeout: {worker_timeout} 秒")
    print(f"  - 等待超時: {wait_timeout} 秒")
    print(f"  - 文檔目錄: {DOCS_DIR}")
    
    # 登入
    print(f"\n🔐 登入...")
    token = login()
    if not token:
        print("❌ 無法登入，退出")
        sys.exit(1)
    
    # 初始化進度追蹤器
    tracker = ProcessingProgressTracker(PROGRESS_FILE)
    
    # 發現所有 Markdown 文件
    print(f"\n📁 掃描文檔目錄...")
    md_files = list(DOCS_DIR.rglob("*.md"))
    
    # 過濾掉不需要的文件
    filtered_files = []
    for md_file in md_files:
        if md_file.name.startswith(".") or md_file.name.lower() == "readme.md":
            continue
        filtered_files.append(md_file)
    
    # 按文件大小排序（小文件優先）
    filtered_files.sort(key=lambda f: f.stat().st_size)
    
    total_files = len(filtered_files)
    print(f"  ✅ 找到 {total_files} 個文件")
    
    tracker.progress_data["summary"]["total_files"] = total_files
    tracker.save_progress()
    
    # 處理每個文件
    processed_count = 0
    failed_count = 0
    
    print(f"\n📝 開始處理文件...")
    print("=" * 80)
    
    for idx, md_file in enumerate(filtered_files, 1):
        if _should_stop:
            print("\n⚠️  收到停止信號，中止處理")
            break
        
        filename = md_file.name
        file_size = md_file.stat().st_size
        
        print(f"\n[{idx}/{total_files}] 處理文件: {filename} ({file_size:,} bytes)")
        
        # 上傳文件
        file_id = upload_file(md_file, token)
        if not file_id:
            failed_count += 1
            tracker.update_file_status(filename, "failed", error="文件上傳失敗")
            continue
        
        # 添加文件記錄
        tracker.add_file_record(filename, file_id, file_size)
        
        # 等待處理完成
        processing_result = wait_for_processing(file_id, token, wait_timeout)
        
        # 檢查結果
        if processing_result["status"] == "completed":
            processed_count += 1
            
            # 獲取 KG 結果
            kg_results = get_kg_results(file_id, token)
            entities_count = len(kg_results.get("entities", []))
            relations_count = len(kg_results.get("relations", []))
            
            # 更新進度
            tracker.update_file_status(
                filename,
                "completed",
                file_id=file_id,
                total_time=processing_result.get("total_time"),
                entities_count=entities_count,
                relations_count=relations_count,
            )
            
            print(f"  ✅ 處理成功: {entities_count} 個實體, {relations_count} 個關係")
            
        elif processing_result["status"] in ["failed", "timeout"]:
            failed_count += 1
            error = processing_result.get('error', 'Unknown error')
            print(f"  ❌ 處理失敗: {error}")
            tracker.update_file_status(filename, "failed", error=error)
            
            # 如果超時，考慮中止
            if processing_result["status"] == "timeout" and failed_count >= 3:
                print(f"\n⚠️  連續 {failed_count} 個文件失敗，建議檢查服務狀態")
                response = input("是否繼續處理？(y/n): ")
                if response.lower() != 'y':
                    break
        
        # 短暫休息
        if idx < total_files:
            time.sleep(1)
    
    # 總結
    print("\n" + "=" * 80)
    print("📊 處理完成總結")
    print("=" * 80)
    print(f"  總文件數: {total_files}")
    print(f"  成功處理: {processed_count}")
    print(f"  失敗: {failed_count}")
    print(f"\n進度記錄已保存到: {PROGRESS_FILE}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
