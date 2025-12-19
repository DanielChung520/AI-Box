# 代碼功能說明: CrewAI 整合模組
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""CrewAI 多角色協作引擎整合模組。"""

from agents.crewai.factory import CrewAIWorkflowFactory
from agents.crewai.llm_adapter import OllamaLLMAdapter
from agents.crewai.manager import CrewManager
from agents.crewai.process_engine import ProcessEngine
from agents.crewai.settings import CrewAISettings, load_crewai_settings
from agents.crewai.workflow import CrewAIWorkflow

__all__ = [
    "CrewAISettings",
    "load_crewai_settings",
    "OllamaLLMAdapter",
    "CrewManager",
    "ProcessEngine",
    "CrewAIWorkflow",
    "CrewAIWorkflowFactory",
]
