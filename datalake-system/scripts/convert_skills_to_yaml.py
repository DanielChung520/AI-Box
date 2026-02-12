# ========================================
# Skills to YAML Workflow 轉換工具
# ========================================
# 功能：將 skills.md 轉換為可執行的 YAML Workflow
# 用法：python scripts/convert_skills_to_yaml.py
# ========================================

import re
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).parent.parent / "mm_agent" / "workflows"

ACTION_KEYWORDS = {
    "data_query": ["查詢", "拉取", "提供", "獲取"],
    "computation": ["計算", "分析", "處理", "比較", "生成"],
    "knowledge_retrieval": ["搜尋", "彙整", "了解", "理論"],
    "response_generation": ["報告", "回覆", "通知"],
    "data_cleaning": ["檢查", "確認", "驗證", "清洗"],
}


def get_action(text):
    for act, kws in ACTION_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                return act
    return "data_query"


def convert_skills_to_yaml():
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

    content = open(
        WORKFLOWS_DIR.parent / "skills" / "skills.md", "r", encoding="utf-8"
    ).read()

    blocks = content.split("\n---\n")
    print(f"找到 {len(blocks)} 個區塊\n")

    count = 0
    for block in blocks:
        if "name:" not in block or "steps:" not in block:
            continue

        name_match = re.search(r"name:\s*(\w+)", block)
        goal_match = re.search(r'goal:\s*"([^"]+)"', block)

        steps_section = re.search(r"steps:\s*\n((?:.|\n)*?)(?=\n\s*(?:outputs|rules|triggers):|$)", block)
        steps = re.findall(r'- "([^"]+)"', steps_section.group(1)) if steps_section else []

        triggers_section = re.search(r"triggers:\s*\n((?:.|\n)*?)(?=\n---|$)", block)
        triggers = re.findall(r'- "([^"]+)"', triggers_section.group(1)) if triggers_section else []

        if not name_match or not steps:
            continue

        name = name_match.group(1)
        goal = goal_match.group(1) if goal_match else ""

        yaml_steps = ""
        for i, step in enumerate(steps, 1):
            act = get_action(step)
            desc = step[:40] + "..." if len(step) > 40 else step
            yaml_steps += f'''    - step_id: {i}
      action_type: "{act}"
      description: "{desc}"
      instruction: |
        {step}
'''

        yaml_content = f'''# ========================================
# Workflow: {name}
# ========================================

name: "{name}"
description: "{goal}"
version: "1.0.0"

'''
        if triggers:
            yaml_content += "triggers:\n"
            for t in triggers[:3]:
                yaml_content += f'  - "{t}"\n'
            yaml_content += "\n"

        yaml_content += "workflow:\n  steps:\n" + yaml_steps

        filepath = WORKFLOWS_DIR / f"{name}.yaml"
        open(filepath, "w", encoding="utf-8").write(yaml_content)
        print(f"✅ {name}.yaml ({len(steps)} steps, {len(triggers)} triggers)")
        count += 1

    print(f"\n完成！產生 {count} 個 workflow YAML")


if __name__ == "__main__":
    convert_skills_to_yaml()
