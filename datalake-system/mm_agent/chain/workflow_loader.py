# ========================================
# Workflow Loader - 從 YAML 載入工作流程配置
# ========================================
# 功能：讀取 workflows/ 目錄下的 YAML 檔案，提供工作流模板供 ReAct Planner 使用
# ========================================

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

WORKFLOW_DIR = Path(__file__).parent.parent / "workflows"


@dataclass
class WorkflowStep:
    """工作流步驟"""
    step_id: int
    action_type: str
    description: str
    instruction: str


@dataclass
class Workflow:
    """工作流定義"""
    name: str
    description: str
    version: str
    triggers: List[str]
    steps: List[WorkflowStep]


class WorkflowLoader:
    """工作流載入器"""

    def __init__(self, workflow_dir: Path = WORKFLOW_DIR):
        self.workflow_dir = workflow_dir
        self._workflows: Dict[str, Workflow] = {}
        self._load_all_workflows()

    def _load_all_workflows(self):
        """載入所有 YAML 工作流配置"""
        if not self.workflow_dir.exists():
            logger.warning(f"Workflow 目錄不存在: {self.workflow_dir}")
            return

        yaml_files = list(self.workflow_dir.glob("*.yaml"))
        logger.info(f"找到 {len(yaml_files)} 個 workflow YAML 檔案")

        for yaml_file in yaml_files:
            try:
                workflow = self._load_workflow(yaml_file)
                if workflow:
                    self._workflows[workflow.name] = workflow
                    logger.info(f"已載入 workflow: {workflow.name} (v{workflow.version})")
            except Exception as e:
                logger.error(f"載入 workflow 失敗 {yaml_file}: {e}")

    def _load_workflow(self, file_path: Path) -> Optional[Workflow]:
        """載入單個工作流"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        steps = []
        for step_data in data.get("workflow", {}).get("steps", []):
            step = WorkflowStep(
                step_id=step_data.get("step_id", 0),
                action_type=step_data.get("action_type", ""),
                description=step_data.get("description", ""),
                instruction=step_data.get("instruction", ""),
            )
            steps.append(step)

        return Workflow(
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            triggers=data.get("triggers", []),
            steps=steps,
        )

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """取得指定名稱的工作流"""
        return self._workflows.get(name)

    def match_workflow(self, instruction: str) -> Optional[Workflow]:
        """根據指令匹配工作流"""
        instruction_lower = instruction.lower()

        for workflow in self._workflows.values():
            for trigger in workflow.triggers:
                trigger_lower = trigger.lower()
                if trigger_lower in instruction_lower:
                    logger.info(f"匹配到 workflow: {workflow.name}")
                    return workflow

        return None

    def generate_prompt_section(self, workflow: Workflow) -> str:
        """生成工作流提示區塊"""
        steps_json = []
        for step in workflow.steps:
            steps_json.append(
                f'''{{"step_id": {step.step_id}, "action_type": "{step.action_type}", "description": "{step.description}", "instruction": "{step.instruction.replace(chr(10), " ").strip()}"}}'''
            )

        return f"""# 工作流：{workflow.name}
# 版本：{workflow.version}
# 說明：{workflow.description}

[
{",\n".join(steps_json)}
]
"""

    def list_workflows(self) -> List[str]:
        """列出所有已載入的工作流"""
        return list(self._workflows.keys())


# 全域實例
_workflow_loader: Optional[WorkflowLoader] = None


def get_workflow_loader() -> WorkflowLoader:
    """取得全域工作流載入器"""
    global _workflow_loader
    if _workflow_loader is None:
        _workflow_loader = WorkflowLoader()
    return _workflow_loader


def match_and_generate_prompt(instruction: str) -> Optional[str]:
    """匹配工作流並生成提示區塊"""
    loader = get_workflow_loader()
    workflow = loader.match_workflow(instruction)

    if workflow:
        return loader.generate_prompt_section(workflow)

    return None


if __name__ == "__main__":
    # 測試載入器
    loader = WorkflowLoader()
    print("已載入的工作流：")
    for name in loader.list_workflows():
        print(f"  - {name}")
