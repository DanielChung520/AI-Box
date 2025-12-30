# Web 搜索工具环境变量配置说明

## 📋 概述

Web 搜索工具需要配置以下环境变量才能正常工作。工具支持多个搜索提供商，按优先级自动降级：

1. **Serper.dev**（首選，便宜快速）
2. **SerpAPI**（備用，功能全）
3. **ScraperAPI**（備用，大量爬取）
4. **Google CSE**（最後，官方但貴）

## 🔑 必需的环境变量

### 1. Serper.dev（推荐，至少配置一个）

```bash
# Serper.dev API Key
# 獲取地址: https://serper.dev/api-key
SERPER_API_KEY=your_serper_api_key_here
```

### 2. SerpAPI（可选，作为备用）

```bash
# SerpAPI API Key
# 獲取地址: https://serpapi.com/
SERPAPI_API_KEY=your_serpapi_key_here
```

### 3. ScraperAPI（可选，作为备用）

```bash
# ScraperAPI API Key
# 獲取地址: https://www.scraperapi.com/
SCRAPER_API_KEY=your_scraper_key_here
```

### 4. Google Custom Search Engine（可选，作为最后备用）

```bash
# Google Custom Search Engine API Key
# 獲取地址: https://console.cloud.google.com/
GOOGLE_CSE_API_KEY=your_google_api_key_here

# Google Custom Search Engine ID（與 GOOGLE_CSE_API_KEY 配對使用）
# 獲取地址: https://cse.google.com/
GOOGLE_CSE_CX=your_google_cse_id_here
```

## 📝 配置步骤

### 步骤 1：编辑 `.env` 文件

在项目根目录的 `.env` 文件中添加上述环境变量。

**重要**：请参考 `docs/系统设计文档/tools/Web搜索工具实现说明.md` 文档获取实际的 API key 值，或从相应的服务提供商获取您自己的 API key。

```bash
# ==================== Web 搜索工具配置 ====================
# Serper.dev API Key（首選，便宜快速）
# 獲取地址: https://serper.dev/api-key
# 文檔參考: docs/系统设计文档/tools/Web搜索工具实现说明.md
SERPER_API_KEY=your_serper_api_key_here

# SerpAPI API Key（備用，功能全）
# 獲取地址: https://serpapi.com/
# 文檔參考: docs/系统设计文档/tools/Web搜索工具实现说明.md
SERPAPI_API_KEY=your_serpapi_key_here

# ScraperAPI API Key（備用，大量爬取）
# 獲取地址: https://www.scraperapi.com/
# 文檔參考: docs/系统设计文档/tools/Web搜索工具实现说明.md
SCRAPER_API_KEY=your_scraper_key_here

# Google Custom Search Engine API Key（最後備用，官方但貴）
# 獲取地址: https://console.cloud.google.com/
# 文檔參考: docs/系统设计文档/tools/Web搜索工具实现说明.md
GOOGLE_CSE_API_KEY=your_google_api_key_here

# Google Custom Search Engine ID（與 GOOGLE_CSE_API_KEY 配對使用）
# 獲取地址: https://cse.google.com/
# 文檔參考: docs/系统设计文档/tools/Web搜索工具实现说明.md
GOOGLE_CSE_CX=your_google_cse_id_here
```

### 步骤 2：重启服务

配置完成后，需要重启后端服务以使环境变量生效：

```bash
# 如果使用 Docker
docker-compose restart api

# 如果直接运行
# 停止当前服务，然后重新启动
```

### 步骤 3：验证配置

可以通过以下方式验证配置是否生效：

1. **检查后端日志**：启动服务时，如果配置正确，应该不会看到工具初始化错误
2. **测试搜索功能**：在前端激活上网功能，发送搜索请求，查看后端日志

## ⚠️ 注意事项

1. **至少配置一个提供商**：系统至少需要一个可用的搜索提供商才能正常工作
2. **优先级顺序**：系统会按优先级顺序尝试使用提供商，如果第一个失败会自动降级到下一个
3. **API Key 安全**：
   - 不要将 API keys 提交到版本控制系统
   - `.env` 文件应该已经在 `.gitignore` 中
   - 生产环境建议使用密钥管理服务

## 🔍 故障排查

### 问题 1：工具初始化失败

**错误信息**：`至少需要配置一個搜索提供商`

**解决方案**：

- 检查 `.env` 文件中是否至少配置了一个 API key
- 确认环境变量名称拼写正确
- 重启服务使配置生效

### 问题 2：搜索请求失败

**错误信息**：`All search providers failed`

**解决方案**：

- 检查 API keys 是否有效
- 检查网络连接
- 查看后端日志获取详细错误信息
- 尝试配置多个提供商以提高可用性

### 问题 3：环境变量未生效

**解决方案**：

- 确认 `.env` 文件在项目根目录
- 确认环境变量名称正确（区分大小写）
- 重启服务
- 检查是否有其他环境变量覆盖了配置

## 📚 相关文档

- [Web 搜索工具实现说明](./系统设计文档/tools/Web搜索工具实现说明.md)
- [Web 搜索工具 ArangoDB 注册说明](./系统设计文档/tools/Web搜索工具ArangoDB注册说明.md)
