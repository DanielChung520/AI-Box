# 代碼功能說明: 自動化代碼質量檢查腳本
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""
自動化代碼質量檢查腳本

用法:
    python check_code_quality.py <文件路徑或目錄>

示例:
    python check_code_quality.py agents/task_analyzer/analyzer.py
    python check_code_quality.py agents/
"""

import subprocess
import sys
from pathlib import Path
from typing import List


def run_command(cmd: List[str], description: str) -> bool:
    """運行命令並返回是否成功"""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        print(f"✅ {description} 通過\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失敗")
        if e.stdout:
            print("標準輸出:")
            print(e.stdout)
        if e.stderr:
            print("錯誤輸出:")
            print(e.stderr)
        print()
        return False


def check_code_quality(target: str) -> bool:
    """檢查代碼質量"""
    target_path = Path(target)

    if not target_path.exists():
        print(f"❌ 錯誤: 文件或目錄不存在: {target}")
        return False

    print(f"🔍 檢查目標: {target}\n")

    # 1. Black 格式化
    if not run_command(["python", "-m", "black", str(target_path)], "運行 Black 格式化"):
        return False

    # 2. Ruff 檢查
    if not run_command(["python", "-m", "ruff", "check", "--fix", str(target_path)], "運行 Ruff 檢查"):
        return False

    # 3. Mypy 檢查
    if not run_command(["python", "-m", "mypy", str(target_path)], "運行 Mypy 類型檢查"):
        return False

    print("🎉 所有檢查通過！")
    return True


def main() -> None:
    """主函數"""
    if len(sys.argv) < 2:
        print("❌ 錯誤: 請指定要檢查的文件或目錄")
        print(f"用法: {sys.argv[0]} <文件路徑或目錄>")
        sys.exit(1)

    target = sys.argv[1]

    if not check_code_quality(target):
        sys.exit(1)


if __name__ == "__main__":
    main()
