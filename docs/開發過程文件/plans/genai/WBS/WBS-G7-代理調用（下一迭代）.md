<!--
代碼功能說明: WBS-G7 代理調用（下一迭代）
創建日期: 2025-12-13 13:55 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 15:49 (UTC+8)
-->

# WBS-G7：代理調用（下一迭代）

## 目標

在模型入口穩定後，再把「Auto/指定 Agent」接入同一個輸入框流程。

## 範圍（下一迭代）

- Auto agent selection（依 task_analyzer）
- 指定 agent_id 呼叫
- **任務型 Agent 池**：Security / Status / Report / WebCrawler / Knowledge（等）
- **每個子任務/每個 Agent 綁定不同模型策略**
  - 例：Security 用高可靠模型；WebCrawler/整理用低成本模型；Report 用長上下文模型
- Agent 執行過程的 context/memory 注入與回寫

## 依賴

- M1-M3（模型入口 + 上下文）完成

## 驗收

- 輸入框支援：Auto agent 或指定 agent_id
- task_analyzer 產出：workflow + agent_plan + per_agent_model_policy（至少 provider/model 或 policy）
- orchestrator 可按 plan 分派任務，並在每次 agent/tool call 上紀錄使用模型與成本/延遲
