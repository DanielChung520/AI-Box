#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChromaDB 清理腳本

用於遷移後清理 ChromaDB 數據和目錄。

用法：
    python3 scripts/cleanup_chromadb.py [--force]

注意事項：
1. 此腳本會刪除所有 ChromaDB 數據，執行前請確認
2. 建議先備份數據
3. 執行後無法恢復
"""

import os
import shutil
import sys
from pathlib import Path

CHROMADB_DATA_DIR = Path("./data/datasets/chromadb")
CHROMA_SQLITE_FILE = Path("./data/datasets/chromadb/chroma.sqlite3")


def cleanup_chromadb_data(force: bool = False) -> bool:
    """
    清理 ChromaDB 數據

    Args:
        force: 是否強制執行（不詢問確認）

    Returns:
        是否成功
    """
    print("=" * 60)
    print("ChromaDB 數據清理工具")
    print("=" * 60)

    # 檢查數據目錄是否存在
    if not CHROMADB_DATA_DIR.exists():
        print(f"✅ ChromaDB 數據目錄不存在: {CHROMADB_DATA_DIR}")
        print("無需清理")
        return True

    # 計算數據大小
    total_size = 0
    file_count = 0
    dir_count = 0

    for item in CHROMADB_DATA_DIR.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size
            file_count += 1
        elif item.is_dir():
            dir_count += 1

    size_mb = total_size / (1024 * 1024)

    print("\n📊 ChromaDB 數據統計：")
    print(f"   目錄數: {dir_count}")
    print(f"   文件數: {file_count}")
    print(f"   總大小: {size_mb:.2f} MB")
    print(f"   路徑: {CHROMADB_DATA_DIR}")

    # 確認執行
    if not force:
        print("\n⚠️  警告：此操作將刪除所有 ChromaDB 數據！")
        response = input("\n是否繼續清理？(輸入 'yes' 確認): ")
        if response.lower() != "yes":
            print("已取消")
            return False

    # 執行清理
    print("\n🗑️  開始清理...")

    try:
        # 刪除數據目錄
        if CHROMADB_DATA_DIR.exists():
            shutil.rmtree(CHROMADB_DATA_DIR)
            print(f"   ✅ 刪除目錄: {CHROMADB_DATA_DIR}")

        # 刪除 SQLite 文件
        if CHROMA_SQLITE_FILE.exists():
            CHROMA_SQLITE_FILE.unlink()
            print(f"   ✅ 刪除文件: {CHROMA_SQLITE_FILE}")

        print("\n✅ 清理完成！")
        print("\n📝 說明：")
        print("   - ChromaDB 數據已完全刪除")
        print("   - 如需回滾到 ChromaDB，需重新處理所有文件")
        print("   - 建議：現在可以安全地卸載 ChromaDB Docker 容器")

        return True

    except Exception as e:
        print(f"\n❌ 清理失敗: {e}")
        return False


def cleanup_docker_container() -> bool:
    """
    清理 ChromaDB Docker 容器

    Returns:
        是否成功
    """
    print("\n" + "=" * 60)
    print("ChromaDB Docker 容器清理")
    print("=" * 60)

    # 停止並刪除容器
    os.system("docker stop chromadb 2>/dev/null || true")
    os.system("docker rm chromadb 2>/dev/null || true")

    # 刪除鏡像（可選）
    print("\n💡 提示：ChromaDB 鏡像仍保留，可執行以下命令刪除：")
    print("   docker rmi chromadb/chroma:latest")

    return True


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="ChromaDB 清理工具")
    parser.add_argument("--force", action="store_true", help="強制執行，不詢問確認")
    parser.add_argument("--all", action="store_true", help="同時清理 Docker 容器")

    args = parser.parse_args()

    # 清理數據
    success = cleanup_chromadb_data(force=args.force)

    if success and args.all:
        # 清理 Docker 容器
        cleanup_docker_container()

    # 退出
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
