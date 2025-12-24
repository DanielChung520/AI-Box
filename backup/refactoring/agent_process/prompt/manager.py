# 代碼功能說明: Prompt Manager 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Prompt Manager - 實現提示模板管理"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """提示模板定義"""

    name: str
    template: str
    description: str = ""
    variables: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class PromptManager:
    """提示管理器"""

    def __init__(self):
        """初始化提示管理器"""
        self._templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self):
        """加載默認模板"""
        # 任務分析模板
        self.register(
            name="task_analysis",
            template="請分析以下任務：\n{task}\n\n上下文信息：\n{context}",
            description="任務分析提示模板",
            variables=["task", "context"],
        )

        # 計劃生成模板
        self.register(
            name="plan_generation",
            template="請為以下任務生成執行計劃：\n{task}\n\n要求：\n{requirements}",
            description="計劃生成提示模板",
            variables=["task", "requirements"],
        )

        # 結果驗證模板
        self.register(
            name="result_validation",
            template="請驗證以下執行結果：\n{result}\n\n預期目標：\n{expected}",
            description="結果驗證提示模板",
            variables=["result", "expected"],
        )

    def register(
        self,
        name: str,
        template: str,
        description: str = "",
        variables: Optional[list[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        註冊提示模板

        Args:
            name: 模板名稱
            template: 模板內容
            description: 模板描述
            variables: 模板變量列表
            metadata: 元數據

        Returns:
            是否成功註冊
        """
        try:
            # 提取模板變量
            if variables is None:
                variables = self._extract_variables(template)

            prompt_template = PromptTemplate(
                name=name,
                template=template,
                description=description,
                variables=variables,
                metadata=metadata or {},
            )

            self._templates[name] = prompt_template
            logger.info(f"Registered prompt template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to register prompt template '{name}': {e}")
            return False

    def _extract_variables(self, template: str) -> list[str]:
        """
        從模板中提取變量

        Args:
            template: 模板內容

        Returns:
            變量列表
        """
        import re

        # 匹配 {variable} 格式的變量
        pattern = r"\{(\w+)\}"
        variables = re.findall(pattern, template)
        return list(set(variables))  # 去重

    def get(self, name: str) -> Optional[PromptTemplate]:
        """
        獲取提示模板

        Args:
            name: 模板名稱

        Returns:
            提示模板，如果不存在則返回 None
        """
        return self._templates.get(name)

    def render(
        self,
        name: str,
        **kwargs: Any,
    ) -> str:
        """
        渲染提示模板

        Args:
            name: 模板名稱
            **kwargs: 模板變量值

        Returns:
            渲染後的提示文本
        """
        template = self.get(name)
        if not template:
            raise ValueError(f"Prompt template '{name}' not found")

        try:
            # 使用 str.format 渲染模板
            rendered = template.template.format(**kwargs)
            logger.debug(f"Rendered prompt template: {name}")
            return rendered
        except KeyError as e:
            logger.error(f"Missing variable in template '{name}': {e}")
            raise ValueError(f"Missing required variable: {e}")
        except Exception as e:
            logger.error(f"Failed to render template '{name}': {e}")
            raise

    def list_templates(self) -> list[PromptTemplate]:
        """
        列出所有模板

        Returns:
            模板列表
        """
        return list(self._templates.values())

    def update(
        self,
        name: str,
        template: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新提示模板

        Args:
            name: 模板名稱
            template: 新的模板內容
            description: 新的描述
            metadata: 新的元數據

        Returns:
            是否成功更新
        """
        prompt_template = self.get(name)
        if not prompt_template:
            logger.warning(f"Prompt template '{name}' not found")
            return False

        try:
            if template is not None:
                prompt_template.template = template
                prompt_template.variables = self._extract_variables(template)
            if description is not None:
                prompt_template.description = description
            if metadata is not None:
                prompt_template.metadata.update(metadata)

            prompt_template.updated_at = datetime.now()
            logger.info(f"Updated prompt template: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update prompt template '{name}': {e}")
            return False

    def delete(self, name: str) -> bool:
        """
        刪除提示模板

        Args:
            name: 模板名稱

        Returns:
            是否成功刪除
        """
        if name not in self._templates:
            logger.warning(f"Prompt template '{name}' not found")
            return False

        del self._templates[name]
        logger.info(f"Deleted prompt template: {name}")
        return True
