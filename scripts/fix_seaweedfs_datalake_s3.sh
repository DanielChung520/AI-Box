#!/bin/bash
# 修復 SeaweedFS Datalake S3 API 配置

echo "🔧 修復 SeaweedFS Datalake S3 API 配置..."
echo "=" | head -c 60 && echo ""

# 創建 S3 配置目錄
mkdir -p /tmp/seaweedfs-datalake-s3-config

# 創建 S3 配置文件
cat > /tmp/seaweedfs-datalake-s3-config/s3.json << 'CONFIG'
{
  "identities": [
    {
      "name": "admin",
      "credentials": [
        {
          "accessKey": "admin",
          "secretKey": "admin123"
        }
      ],
      "actions": [
        "Admin",
        "Read",
        "Write"
      ]
    }
  ]
}
CONFIG

echo "✅ S3 配置文件已創建"
echo ""
echo "📋 下一步操作："
echo "1. 停止現有容器："
echo "   docker-compose -f docker-compose.seaweedfs-datalake.yml down"
echo ""
echo "2. 創建 Docker volume 並複製配置："
echo "   docker volume create seaweedfs-datalake-s3-config"
echo "   docker run --rm -v /tmp/seaweedfs-datalake-s3-config:/source -v seaweedfs-datalake-s3-config:/target alpine sh -c 'cp -r /source/* /target/'"
echo ""
echo "3. 重新啟動容器："
echo "   docker-compose -f docker-compose.seaweedfs-datalake.yml up -d"
echo ""
echo "4. 檢查日誌確認 S3 API 已啟動："
echo "   docker logs seaweedfs-datalake-filer | grep -i s3"
