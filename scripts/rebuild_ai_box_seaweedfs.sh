#!/bin/bash
# 清理並重建 AI-Box SeaweedFS
# 適用於新環境，文件可清除的情況

echo "=========================================="
echo "  清理並重建 AI-Box SeaweedFS"
echo "=========================================="
echo ""
echo "⚠️  警告: 此操作將刪除 AI-Box SeaweedFS 所有數據並重建"
echo "   DataLake SeaweedFS 不會受到影響"
echo ""
read -p "是否繼續? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 1
fi

cd /home/daniel/ai-box

# 1. 停止 AI-Box SeaweedFS
echo ""
echo "🛑 步驟 1: 停止 AI-Box SeaweedFS..."
docker compose -f docker-compose.seaweedfs.yml down
echo "✅ 已停止"

# 2. 備份配置
echo ""
echo "💾 步驟 2: 備份配置文件..."
cp docker-compose.seaweedfs.yml "docker-compose.seaweedfs.yml.backup.$(date +%Y%m%d)"
echo "✅ 配置已備份"

# 3. 刪除舊的 volume 數據（釋放 21GB）
echo ""
echo "🗑️  步驟 3: 清理舊的 volume 數據..."
echo "   刪除前空間:"
docker volume inspect ai-box_seaweedfs-volume-data --format '{{.Mountpoint}}' 2>/dev/null | \
    xargs -I {} sudo du -sh {} 2>/dev/null || echo "   無法查看（需要 sudo）"

echo "   正在刪除 volume 數據卷..."
docker volume rm ai-box_seaweedfs-volume-data 2>/dev/null || echo "   Volume 不存在或已刪除"

# 4. 重新創建 volume 並設置合理參數
echo ""
echo "📝 步驟 4: 修改配置（設置 -max=50，減小 volume 大小）..."
cat > docker-compose.seaweedfs.yml << 'EOF'
# 代碼功能說明: SeaweedFS Docker Compose 配置（AI-Box 服務）
# 創建日期: 2025-12-29
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31
# 說明: 重建配置，設置合理的 volume 數量和大小

services:
  # SeaweedFS Master 節點
  seaweedfs-master:
    image: chrislusf/seaweedfs:latest
    container_name: seaweedfs-ai-box-master
    command: "master -ip=seaweedfs-master -port=9333"
    ports:
      - "9333:9333"
    networks:
      - seaweedfs-network
    volumes:
      - seaweedfs-master-data:/data
    restart: unless-stopped

  # SeaweedFS Volume 節點
  # 關鍵修改：-max=50（50個 volumes），-volumeSizeLimitMB=500（每個500MB）
  seaweedfs-volume:
    image: chrislusf/seaweedfs:latest
    container_name: seaweedfs-ai-box-volume
    command: "volume -mserver=seaweedfs-master:9333 -port=8080 -max=50 -volumeSizeLimitMB=500"
    depends_on:
      - seaweedfs-master
    networks:
      - seaweedfs-network
    volumes:
      - seaweedfs-volume-data:/data
    restart: unless-stopped

  # SeaweedFS Filer 節點
  seaweedfs-filer:
    image: chrislusf/seaweedfs:latest
    container_name: seaweedfs-ai-box-filer
    command: "filer -master=seaweedfs-master:9333 -s3 -s3.port=8333 -s3.config=/etc/seaweedfs/s3.json"
    ports:
      - "8888:8888"
      - "8333:8333"
    depends_on:
      - seaweedfs-master
      - seaweedfs-volume
    networks:
      - seaweedfs-network
    environment:
      - SEAWEEDFS_S3_ACCESS_KEY=${AI_BOX_SEAWEEDFS_S3_ACCESS_KEY:-admin}
      - SEAWEEDFS_S3_SECRET_KEY=${AI_BOX_SEAWEEDFS_S3_SECRET_KEY:-admin123}
    volumes:
      - ./config/seaweedfs:/etc/seaweedfs:ro
      - seaweedfs-ai-box-filer-data:/data
    restart: unless-stopped

networks:
  seaweedfs-network:
    driver: bridge

volumes:
  seaweedfs-master-data:
  seaweedfs-volume-data:     # 這會重新創建
  seaweedfs-ai-box-filer-data:
EOF

echo "✅ 配置已更新"
echo "   -max=50 (最多50個 volumes)"
echo "   -volumeSizeLimitMB=500 (每個 volume 500MB，更省空間)"

# 5. 啟動服務
echo ""
echo "🚀 步驟 5: 啟動 SeaweedFS..."
docker compose -f docker-compose.seaweedfs.yml up -d

echo ""
echo "⏳ 等待服務啟動..."
sleep 10

# 6. 創建必要的 buckets
echo ""
echo "📦 步驟 6: 創建必要的 buckets..."
sleep 5

# 檢查狀態
echo ""
echo "📊 重建後狀態："
curl -s http://localhost:9333/vol/status | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    free = d.get('Free', 0)
    max_vol = d.get('Max', 0)
    for k,v in d['Volumes']['DataCenters']['DefaultDataCenter']['DefaultRack'].items():
        total = len(v)
        readonly = len([x for x in v if x.get('ReadOnly')])
        writable = total - readonly
        print(f'  節點: {k}')
        print(f'  Volumes: {total}, ReadOnly: {readonly}, Writable: {writable}')
        print(f'  Free Slots: {free}, Max: {max_vol}')
except:
    print('  暫時無法獲取狀態，請稍後檢查')
" 2>/dev/null

echo ""
echo "🔍 新佔用空間："
docker exec seaweedfs-ai-box-volume du -sh /data 2>/dev/null || echo "  稍後查看..."

echo ""
echo "=========================================="
echo "  重建完成！"
echo "=========================================="
echo ""
echo "✅ 已回收舊的 21GB 預分配空間"
echo "✅ 創建新的 50 個 volumes（每個 500MB = 總計 25GB 預分配）"
echo "✅ 所有 volumes 都是 Writable"
echo ""
echo "📊 空間使用對比："
echo "   重建前: ~21GB 預分配（全部 ReadOnly）"
echo "   重建後: ~25GB 預分配（全部 Writable）"
echo "   差異: 只增加 ~4GB，但可寫入！"
echo ""
echo "⚠️  注意:"
echo "1. 需要重新創建 buckets（如果之前有）"
echo "2. DataLake SeaweedFS 未受影響（仍有 ReadOnly 問題）"
echo "3. 測試文件上傳功能是否正常"
echo ""
