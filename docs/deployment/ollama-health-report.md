# Ollama 節點硬體檢查報告

- 報告時間：2025-11-25 23:37:59 CST
- 目標節點：localhost:11434
- 生成工具：scripts/verify_env.sh

## 硬體摘要

| 項目 | 數值 |
|------|------|
| CPU | Apple M4 Pro |
| 記憶體 | 64.00 GiB |
| GPU | Apple M4 Pro |
| 儲存（針對 /） | /dev/disk3s1s1   926Gi    11Gi   731Gi     2%    451k  4.3G    0%   / |

## 容量閾值對照（AI-Box 架構規劃）

| 項目 | 最低需求 | 現況 | 狀態 |
|------|---------|------|------|
| 記憶體 | ≥ 64 GiB（可同時載入 2 個 30B 模型） | 64.00 GiB | ✅ 符合 |
| GPU/NE | ≥ 20 核心（Apple Neural Engine） | Apple M4 Pro（內建 GPU/NE） | ✅ 符合 |
| 儲存 | ≥ 700 GiB 可用空間（模型 + 緩存） | 731 GiB 可用 | ✅ 符合 |
| 網路 | ≥ 1 Gbps（建議） | 待網管檢測 | ⚠ 待確認 |

## Ollama 狀態

- CLI 版本：ollama version is 0.13.0
- API 健康：OK (http://localhost:11434/api/version)

<details>
<summary>模型清單</summary>

```
NAME               ID              SIZE     MODIFIED
gpt-oss:20b        17052f91a42e    13 GB    6 days ago
qwen3-coder:30b    06c1097efce0    18 GB    6 days ago
```

</details>
