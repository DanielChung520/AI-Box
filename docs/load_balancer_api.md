# LLM 負載均衡 API 文檔

## 概述

LLM 負載均衡器提供了多個 LLM 提供商的負載均衡功能，支持多種負載均衡策略和健康檢查機制。

## API 端點

### 1. 健康檢查

**端點**: `GET /api/v1/llm/health`

**描述**: 獲取 LLM 服務的健康狀態和提供商狀態。

**響應示例**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "llm",
    "load_balancer": {
      "provider_stats": {...},
      "overall_stats": {...}
    },
    "health_check": {...}
  }
}
```

### 2. 負載均衡器統計

**端點**: `GET /api/v1/llm/load-balancer/stats`

**描述**: 獲取負載均衡器的統計信息。

**響應示例**:
```json
{
  "success": true,
  "data": {
    "provider_stats": {
      "chatgpt": {
        "healthy": true,
        "available": true,
        "weight": 3,
        "active_connections": 2,
        "request_count": 100,
        "success_count": 95,
        "failure_count": 5,
        "success_rate": 0.95,
        "average_latency": 0.5
      }
    },
    "overall_stats": {
      "total_requests": 200,
      "total_success": 190,
      "total_failure": 10,
      "success_rate": 0.95,
      "strategy": "round_robin",
      "provider_count": 5
    }
  }
}
```

### 3. 健康檢查狀態

**端點**: `GET /api/v1/llm/health-check/status`

**描述**: 獲取健康檢查的狀態信息。

**響應示例**:
```json
{
  "success": true,
  "data": {
    "chatgpt": {
      "healthy": true,
      "failure_count": 0,
      "last_check": 1234567890.0,
      "latency": 0.5,
      "error": null
    }
  }
}
```

## 配置

負載均衡器配置位於 `config/config.json` 的 `llm.load_balancer` 部分：

```json
{
  "llm": {
    "load_balancer": {
      "strategy": "round_robin",
      "providers": ["chatgpt", "gemini", "qwen", "grok", "ollama"],
      "weights": {
        "chatgpt": 3,
        "gemini": 2,
        "qwen": 2,
        "grok": 1,
        "ollama": 1
      },
      "cooldown_seconds": 30
    },
    "health_check": {
      "interval": 60.0,
      "timeout": 5.0,
      "failure_threshold": 3
    }
  }
}
```

## 負載均衡策略

1. **round_robin**: 輪詢策略，依次選擇提供商
2. **weighted**: 加權輪詢，根據權重分配請求
3. **least_connections**: 最少連接，選擇當前連接數最少的提供商
4. **latency_based**: 基於延遲，選擇平均延遲最低的提供商
5. **response_time_based**: 基於響應時間，選擇最近響應時間最短的提供商
