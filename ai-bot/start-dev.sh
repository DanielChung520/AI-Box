#!/bin/bash
# 代碼功能說明: 前端開發服務器啟動腳本（帶日誌輪轉）
# 創建日期: 2025-12-08
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-08 12:30:00 UTC+8

LOG_DIR="../logs"
FRONTEND_LOG="$LOG_DIR/frontend.log"
MAX_SIZE=512000  # 500KB

# 確保日誌目錄存在
mkdir -p "$LOG_DIR"

# 日誌輪轉函數
rotate_log() {
    if [ -f "$FRONTEND_LOG" ]; then
        SIZE=$(stat -f%z "$FRONTEND_LOG" 2>/dev/null || stat -c%s "$FRONTEND_LOG" 2>/dev/null)
        if [ "$SIZE" -ge "$MAX_SIZE" ]; then
            # 刪除最舊的備份
            [ -f "${FRONTEND_LOG}.4" ] && rm -f "${FRONTEND_LOG}.4"
            # 輪轉備份文件
            [ -f "${FRONTEND_LOG}.3" ] && mv "${FRONTEND_LOG}.3" "${FRONTEND_LOG}.4"
            [ -f "${FRONTEND_LOG}.2" ] && mv "${FRONTEND_LOG}.2" "${FRONTEND_LOG}.3"
            [ -f "${FRONTEND_LOG}.1" ] && mv "${FRONTEND_LOG}.1" "${FRONTEND_LOG}.2"
            # 將當前日誌重命名為 .1
            mv "$FRONTEND_LOG" "${FRONTEND_LOG}.1"
            # 創建新的日誌文件
            touch "$FRONTEND_LOG"
        fi
    fi
}

# 啟動時輪轉一次
rotate_log

# 啟動 Vite 開發服務器，輸出重定向到日誌文件
# 同時在後台運行日誌輪轉監控
(
    while true; do
        sleep 60
        rotate_log
    done
) &

# 啟動 Vite
pnpm dev:client 2>&1 | tee -a "$FRONTEND_LOG"
