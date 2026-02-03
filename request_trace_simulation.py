#!/usr/bin/env python3
"""
代碼功能說明: AI-Box 請求追蹤模擬腳本 - 模擬從前端輸入到後端回應的完整請求鏈路及時間消耗
創建日期: 2026-02-02
創建人: OpenCode AI
最後修改日期: 2026-02-02

使用參數:
  - user: systemAdmin
  - 模型: Ollama 4
  - 任務: MM-Agent
  - 輸入: "能將採購流程用mermaid 幫我根據TIPTOP的入庫流程嗎？"
"""

import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

# ============================================================
# 模擬數據結構
# ============================================================

class RequestStage(Enum):
    FRONTEND_INPUT = "前端輸入處理"
    API_REQUEST_SEND = "前端API請求發送"
    API_GATEWAY = "API Gateway 路由"
    AUTHENTICATION = "認證授權檢查"
    CONTEXT_MANAGER = "上下文管理"
    MEMORY_RETRIEVAL = "記憶檢索"
    TASK_CLASSIFIER = "任務分類"
    MOE_ROUTING = "MoE 路由選擇"
    LLM_PROVIDER_CALL = "LLM 提供商調用"
    OLLAMA_INFERENCE = "Ollama 模型推理"
    AGENT_DISPATCH = "Agent 分發"
    MM_AGENT_EXECUTION = "MM-Agent 執行"
    RESPONSE_FORMATTING = "響應格式化"
    STREAMING_RESPONSE = "流式響應傳輸"
    FRONTEND_RENDER = "前端渲染顯示"


@dataclass
class StageTiming:
    """階段時間記錄"""
    stage: RequestStage
    start_ms: float
    end_ms: float
    duration_ms: float
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "start_ms": round(self.start_ms, 2),
            "end_ms": round(self.end_ms, 2),
            "duration_ms": round(self.duration_ms, 2),
            "details": self.details
        }


@dataclass
class RequestTrace:
    """完整請求追蹤記錄"""
    request_id: str
    session_id: str
    task_id: str
    user: str
    model: str
    agent: str
    user_input: str
    stages: List[StageTiming] = field(default_factory=list)
    total_latency_ms: float = 0.0

    def add_stage(self, stage: StageTiming):
        self.stages.append(stage)

    def calculate_total_latency(self):
        if self.stages:
            self.total_latency_ms = self.stages[-1].end_ms - self.stages[0].start_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "user": self.user,
            "model": self.model,
            "agent": self.agent,
            "user_input": self.user_input,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "stages": [s.to_dict() for s in self.stages],
            "timestamp": datetime.now().isoformat()
        }


# ============================================================
# 模擬各階段延遲
# ============================================================

class LatencySimulator:
    """延遲模擬器 - 根據實際系統特性模擬各階段時間消耗"""

    # 各階段延遲配置 (ms)
    LATENCY_CONFIG = {
        RequestStage.FRONTEND_INPUT: {
            "min": 5, "max": 20,  # 輸入解析、驗證
            "description": "前端輸入處理和JSON序列化"
        },
        RequestStage.API_REQUEST_SEND: {
            "min": 10, "max": 50,  # 網絡請求發送
            "description": "HTTP請求建立和發送"
        },
        RequestStage.API_GATEWAY: {
            "min": 2, "max": 10,  # Gateway路由
            "description": "FastAPI路由匹配和中間件處理"
        },
        RequestStage.AUTHENTICATION: {
            "min": 5, "max": 30,  # JWT驗證
            "description": "Token解析、用戶認證、權限檢查"
        },
        RequestStage.CONTEXT_MANAGER: {
            "min": 10, "max": 50,  # 上下文窗口管理
            "description": "獲取會話上下文、消息窗口裁剪"
        },
        RequestStage.MEMORY_RETRIEVAL: {
            "min": 50, "max": 200,  # 向量檢索
            "description": "長期記憶檢索、向量相似度搜索(ChromaDB/ArangoDB)"
        },
        RequestStage.TASK_CLASSIFIER: {
            "min": 100, "max": 300,  # Task分類
            "description": "TaskAnalyzer意圖分類、Router LLM調用"
        },
        RequestStage.MOE_ROUTING: {
            "min": 20, "max": 80,  # MoE路由
            "description": "MoE Manager模型選擇、provider過濾"
        },
        RequestStage.LLM_PROVIDER_CALL: {
            "min": 5, "max": 20,  # LLM調用開銷
            "description": "HTTP客戶端請求準備、重試邏輯"
        },
        RequestStage.OLLAMA_INFERENCE: {
            "min": 2000, "max": 8000,  # Ollama推理 (主要瓶頸)
            "description": "Ollama本地模型推理、token生成"
        },
        RequestStage.AGENT_DISPATCH: {
            "min": 20, "max": 100,  # Agent分發
            "description": "Agent選擇、協議轉換、任務封裝"
        },
        RequestStage.MM_AGENT_EXECUTION: {
            "min": 500, "max": 3000,  # MM-Agent執行
            "description": "MM-Agent業務邏輯、數據庫查詢、API調用"
        },
        RequestStage.RESPONSE_FORMATTING: {
            "min": 10, "max": 50,  # 響應格式化
            "description": "響應序列化、Markdown渲染"
        },
        RequestStage.STREAMING_RESPONSE: {
            "min": 5, "max": 30,  # 流式傳輸
            "description": "SSE流式響應傳輸"
        },
        RequestStage.FRONTEND_RENDER: {
            "min": 10, "max": 100,  # 前端渲染
            "description": "React渲染、Markdown解析、mermaid渲染"
        },
    }

    @classmethod
    def simulate_latency(cls, stage: RequestStage) -> float:
        """模擬階段延遲"""
        config = cls.LATENCY_CONFIG.get(stage, {"min": 1, "max": 10})
        # 添加隨機波動
        import random
        base_latency = random.uniform(config["min"], config["max"])
        # 添加網絡波動 (±10%)
        fluctuation = base_latency * random.uniform(-0.1, 0.1)
        return base_latency + fluctuation


# ============================================================
# 請求追蹤模擬器
# ============================================================

class RequestTraceSimulator:
    """請求追蹤模擬器"""

    def __init__(self, user: str, model: str, agent: str, user_input: str):
        self.user = user
        self.model = model
        self.agent = agent
        self.user_input = user_input
        self.request_id = f"req_{int(time.time() * 1000)}_{hash(user_input) % 10000}"
        self.session_id = f"sess_{int(time.time() * 1000)}"
        self.task_id = f"task_{int(time.time() * 1000)}"
        self.trace = RequestTrace(
            request_id=self.request_id,
            session_id=self.session_id,
            task_id=self.task_id,
            user=user,
            model=model,
            agent=agent,
            user_input=user_input
        )
        self.current_time_ms = 0.0

    def _add_stage(self, stage: RequestStage, details: str = ""):
        """添加階段記錄"""
        latency = LatencySimulator.simulate_latency(stage)
        start = self.current_time_ms
        end = start + latency

        stage_timing = StageTiming(
            stage=stage,
            start_ms=start,
            end_ms=end,
            duration_ms=latency,
            details=details or LatencySimulator.LATENCY_CONFIG[stage]["description"]
        )

        self.trace.add_stage(stage_timing)
        self.current_time_ms = end

        return stage_timing

    def _get_model_specific_latency(self) -> Dict[str, float]:
        """根據模型獲取特定延遲配置"""
        if "ollama" in self.model.lower():
            return {
                "llm_inference": 3000,  # Ollama本地推理
                "agent_execution": 1500,  # Agent執行
            }
        elif "gpt" in self.model.lower():
            return {
                "llm_inference": 1500,  # GPT雲端推理
                "agent_execution": 1000,
            }
        else:
            return {
                "llm_inference": 2000,
                "agent_execution": 2000,
            }

    def simulate_full_request(self) -> RequestTrace:
        """模擬完整請求流程"""

        print(f"\n{'='*80}")
        print(f"🚀 請求追蹤模擬開始")
        print(f"{'='*80}")
        print(f"📋 請求參數:")
        print(f"   - 用戶: {self.user}")
        print(f"   - 模型: {self.model}")
        print(f"   - Agent: {self.agent}")
        print(f"   - 輸入: {self.user_input[:50]}...")
        print(f"   - Request ID: {self.request_id}")
        print(f"{'='*80}\n")

        # 1. 前端輸入處理
        stage = self._add_stage(
            RequestStage.FRONTEND_INPUT,
            f"解析用戶輸入 '{self.user_input[:30]}...'，構建請求體"
        )
        print(f"1️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 2. 前端API請求發送
        stage = self._add_stage(
            RequestStage.API_REQUEST_SEND,
            f"發送 POST /api/v1/chat 請求"
        )
        print(f"2️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 3. API Gateway路由
        stage = self._add_stage(
            RequestStage.API_GATEWAY,
            "FastAPI路由匹配，请求重定向到 /chat 端点"
        )
        print(f"3️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 4. 認證授權
        stage = self._add_stage(
            RequestStage.AUTHENTICATION,
            f"JWT Token驗證，用戶: {self.user}，權限檢查"
        )
        print(f"4️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 5. 上下文管理
        stage = self._add_stage(
            RequestStage.CONTEXT_MANAGER,
            f"獲取會話上下文 {self.session_id}，消息窗口裁剪"
        )
        print(f"5️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 6. 記憶檢索
        stage = self._add_stage(
            RequestStage.MEMORY_RETRIEVAL,
            "長期記憶檢索，向量相似度搜索 (ChromaDB/ArangoDB)"
        )
        print(f"6️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 7. 任務分類 (TaskAnalyzer)
        stage = self._add_stage(
            RequestStage.TASK_CLASSIFIER,
            f"TaskAnalyzer意圖分類: 識別為 '{self.agent}' 任務"
        )
        print(f"7️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 8. MoE路由
        stage = self._add_stage(
            RequestStage.MOE_ROUTING,
            f"MoE Manager選擇模型: {self.model}"
        )
        print(f"8️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 9. LLM提供商調用
        stage = self._add_stage(
            RequestStage.LLM_PROVIDER_CALL,
            f"準備 {self.model} API請求，設置超時和重試"
        )
        print(f"9️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 10. Ollama模型推理 (主要瓶頸)
        model_latency = self._get_model_specific_latency()
        stage = self._add_stage(
            RequestStage.OLLAMA_INFERENCE,
            f"Ollama {self.model} 模型推理: '{self.user_input[:30]}...' → Mermaid流程圖"
        )
        print(f"🔟 {stage.stage.value}: {stage.duration_ms:.1f}ms ⏱️ **主要瓶頸**")
        print(f"   📝 {stage.details}")
        print(f"   💡 建議優化: 增加 Ollama 批處理大小、使用 GPU 加速")

        # 11. Agent分發
        stage = self._add_stage(
            RequestStage.AGENT_DISPATCH,
            f"分發到 {self.agent} Agent，協議轉換"
        )
        print(f"1️⃣1️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 12. MM-Agent執行
        stage = self._add_stage(
            RequestStage.MM_AGENT_EXECUTION,
            f"MM-Agent執行 TIPTOP 入庫流程分析，生成 Mermaid 代碼"
        )
        print(f"1️⃣2️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")
        print(f"   📊 MM-Agent 內部流程:")
        print(f"      - 語義分析: 解析用戶需求")
        print(f"      - 數據查詢: 查詢 TIPTOP 入庫流程")
        print(f"      - 流程圖生成: 生成 Mermaid 代碼")
        print(f"      - 結果驗證: 驗證流程圖正確性")

        # 13. 響應格式化
        stage = self._add_stage(
            RequestStage.RESPONSE_FORMATTING,
            "序列化響應，Markdown + Mermaid 渲染"
        )
        print(f"1️⃣3️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 14. 流式響應傳輸
        stage = self._add_stage(
            RequestStage.STREAMING_RESPONSE,
            "SSE 流式傳輸 Mermaid 代碼塊"
        )
        print(f"1️⃣4️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 15. 前端渲染
        stage = self._add_stage(
            RequestStage.FRONTEND_RENDER,
            "React渲染組件，Mermaid流程圖顯示"
        )
        print(f"1️⃣5️⃣ {stage.stage.value}: {stage.duration_ms:.1f}ms")
        print(f"   📝 {stage.details}")

        # 計算總延遲
        self.trace.calculate_total_latency()

        # 打印匯總
        print(f"\n{'='*80}")
        print(f"📊 請求追蹤匯總")
        print(f"{'='*80}")
        print(f"總延遲: {self.trace.total_latency_ms:.1f}ms ({self.trace.total_latency_ms/1000:.2f}s)")
        print(f"\n瓶頸分析:")
        print(f"  🔴 高延遲階段:")
        for stage_timing in sorted(self.trace.stages, key=lambda x: x.duration_ms, reverse=True)[:5]:
            if stage_timing.duration_ms > 500:
                print(f"     - {stage_timing.stage.value}: {stage_timing.duration_ms:.1f}ms ({stage_timing.duration_ms/self.trace.total_latency_ms*100:.1f}%)")

        print(f"\n🟡 中等延遲階段:")
        for stage_timing in sorted(self.trace.stages, key=lambda x: x.duration_ms, reverse=True):
            if 100 < stage_timing.duration_ms <= 500:
                print(f"     - {stage_timing.stage.value}: {stage_timing.duration_ms:.1f}ms ({stage_timing.duration_ms/self.trace.total_latency_ms*100:.1f}%)")

        print(f"\n🟢 低延遲階段:")
        for stage_timing in sorted(self.trace.stages, key=lambda x: x.duration_ms)[:3]:
            if stage_timing.duration_ms <= 100:
                print(f"     - {stage_timing.stage.value}: {stage_timing.duration_ms:.1f}ms ({stage_timing.duration_ms/self.trace.total_latency_ms*100:.1f}%)")

        print(f"\n💡 優化建議:")
        print(f"  1. Ollama 模型推理是最主要瓶頸，建議:")
        print(f"     - 使用 GPU 加速 Ollama")
        print(f"     - 增加 Ollama 批處理大小")
        print(f"     - 考慮使用更小的模型或量化版本")
        print(f"  2. MM-Agent 執行時間較長，建議:")
        print(f"     - 優化 TIPTOP 流程查詢")
        print(f"     - 添加結果緩存")
        print(f"     - 並行化獨立的查詢操作")
        print(f"  3. 記憶檢索可考慮:")
        print(f"     - 增加索引緩存")
        print(f"     - 使用更快的向量數據庫")

        print(f"\n{'='*80}")
        print(f"✨ 模擬完成")
        print(f"{'='*80}\n")

        return self.trace


# ============================================================
# 主程序
# ============================================================

def main():
    """主程序入口"""

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      AI-Box 請求追蹤模擬器                                     ║
║                   Request Trace Simulator for AI-Bot                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # 模擬參數
    params = {
        "user": "systemAdmin",
        "model": "Ollama 4",  # 例如: llama3.2, qwen2.5
        "agent": "MM-Agent",
        "input": "能將採購流程用mermaid 幫我根據TIPTOP的入庫流程嗎？"
    }

    print(f"📥 輸入參數:")
    print(f"   - User: {params['user']}")
    print(f"   - Model: {params['model']}")
    print(f"   - Agent: {params['agent']}")
    print(f"   - Input: {params['input']}")
    print()

    # 創建模擬器並執行
    simulator = RequestTraceSimulator(
        user=params["user"],
        model=params["model"],
        agent=params["agent"],
        user_input=params["input"]
    )

    trace = simulator.simulate_full_request()

    # 保存結果到JSON文件
    output_file = f"/home/daniel/ai-box/request_trace_{trace.request_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(trace.to_dict(), f, ensure_ascii=False, indent=2)

    print(f"📄 追蹤結果已保存到: {output_file}")

    return trace


if __name__ == "__main__":
    main()
