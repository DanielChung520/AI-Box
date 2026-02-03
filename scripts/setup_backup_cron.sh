#!/bin/bash

# 代碼功能說明: 設置定時備份任務
# 創建日期: 2026-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-27

echo "設置 AI-Box 定時備份任務..."
echo ""

# 檢查是否為 macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ 此腳本僅適用於 macOS"
    echo "對於 Linux，請使用 crontab 設置"
    exit 1
fi

# 創建日志目錄
echo "1. 創建日志目錄..."
mkdir -p /Users/daniel/GitHub/AI-Box/logs
echo "✓ logs 目錄已創建"

# 複製 plist 文件
echo ""
echo "2. 複製 launchd plist 文件..."
cp /Users/daniel/GitHub/AI-Box/scripts/com.aibox.backup.plist /tmp/com.aibox.backup.plist
echo "✓ plist 文件已準備"

# 載入 launchd
echo ""
echo "3. 載入 launchd 任務（需要 sudo）..."
sudo launchctl load /tmp/com.aibox.backup.plist
if [ $? -eq 0 ]; then
    echo "✓ launchd 任務已載入"
else
    echo "✗ launchd 任務載入失敗"
    exit 1
fi

# 啟動任務
echo ""
echo "4. 啟動 launchd 任務..."
sudo launchctl start com.aibox.backup
if [ $? -eq 0 ]; then
    echo "✓ launchd 任務已啟動"
else
    echo "✗ launchd 任務啟動失敗"
    exit 1
fi

# 檢查任務狀態
echo ""
echo "5. 檢查任務狀態..."
sudo launchctl list | grep com.aibox.backup
echo ""

# 手動測試備份
echo "6. 手動測試一次備份..."
echo "執行: python scripts/backup_all.py"
cd /Users/daniel/GitHub/AI-Box && .venv/bin/python scripts/backup_all.py
echo ""

# 完成
echo "========================================"
echo "✓ 定時備份任務設置完成！"
echo ""
echo "備份頻率: 每小時"
echo "備份位置: /Users/daniel/GitHub/AI-Box/backups/"
echo "日誌位置:"
echo "  - 標準輸出: /Users/daniel/GitHub/AI-Box/logs/backup.log"
echo "  - 錯誤輸出: /Users/daniel/GitHub/AI-Box/logs/backup.error.log"
echo ""
echo "常用命令:"
echo "  查看日誌: tail -f logs/backup.log"
echo "  手動備份: python scripts/backup_all.py"
echo "  停止任務: sudo launchctl stop com.aibox.backup"
echo "  卸載任務: sudo launchctl unload /Library/LaunchDaemons/com.aibox.backup.plist"
echo "========================================"
