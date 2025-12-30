# 代碼功能說明: 數學計算工具實現
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""數學計算工具

支持基本數學運算、科學計算和安全的表達式求值。
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Any, Dict, Optional

import structlog

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.utils.errors import ToolExecutionError, ToolValidationError

logger = structlog.get_logger(__name__)

# 允許的數學運算符
ALLOWED_OPERATORS: Dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# 允許的數學函數
ALLOWED_FUNCTIONS: Dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    # 數學函數
    "sqrt": math.sqrt,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "degrees": math.degrees,
    "radians": math.radians,
    "pi": math.pi,
    "e": math.e,
    "ceil": math.ceil,
    "floor": math.floor,
    "fabs": math.fabs,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "lcm": math.lcm,
}


class MathInput(ToolInput):
    """數學計算輸入參數"""

    expression: str  # 數學表達式字符串（如 "2 + 3 * 4"）
    operation: Optional[str] = None  # 可選，指定操作類型（如 "add", "multiply"）


class MathOutput(ToolOutput):
    """數學計算輸出結果"""

    result: float  # 計算結果
    expression: str  # 原始表達式


class SafeEvaluator:
    """安全的表達式求值器

    只允許數學運算，禁止執行任意代碼。
    """

    def __init__(self) -> None:
        """初始化安全求值器"""
        self._allowed_names = ALLOWED_FUNCTIONS.copy()

    def evaluate(self, node: ast.AST) -> float:
        """
        遞歸求值 AST 節點

        Args:
            node: AST 節點

        Returns:
            計算結果

        Raises:
            ToolValidationError: 表達式不安全或無效
        """
        if isinstance(node, ast.Num):  # Python < 3.8
            if isinstance(node.n, (int, float)):
                return float(node.n)
            else:
                raise ToolValidationError(
                    f"Unsupported number type: {type(node.n)}", field="expression"
                )
        elif isinstance(node, ast.Constant):  # Python >= 3.8
            if isinstance(node.value, (int, float)):
                return float(node.value)
            else:
                raise ToolValidationError(
                    f"Unsupported constant type: {type(node.value)}", field="expression"
                )
        elif isinstance(node, ast.BinOp):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            op = ALLOWED_OPERATORS.get(type(node.op))
            if op is None:
                raise ToolValidationError(
                    f"Unsupported operator: {type(node.op).__name__}", field="expression"
                )
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self.evaluate(node.operand)
            op = ALLOWED_OPERATORS.get(type(node.op))
            if op is None:
                raise ToolValidationError(
                    f"Unsupported unary operator: {type(node.op).__name__}", field="expression"
                )
            return op(operand)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ToolValidationError(
                    "Only function calls are allowed, not method calls", field="expression"
                )
            func_name = node.func.id
            if func_name not in self._allowed_names:
                raise ToolValidationError(
                    f"Function '{func_name}' is not allowed", field="expression"
                )
            func = self._allowed_names[func_name]
            args = [self.evaluate(arg) for arg in node.args]
            return func(*args)
        elif isinstance(node, ast.Name):
            if node.id in self._allowed_names:
                # 返回常量值（如 pi, e）
                value = self._allowed_names[node.id]
                if isinstance(value, (int, float)):
                    return float(value)
            raise ToolValidationError(f"Name '{node.id}' is not allowed", field="expression")
        else:
            raise ToolValidationError(
                f"Unsupported AST node type: {type(node).__name__}", field="expression"
            )


class MathCalculator(BaseTool[MathInput, MathOutput]):
    """數學計算工具

    支持基本數學運算、科學計算和安全的表達式求值。
    """

    def __init__(self) -> None:
        """初始化數學計算工具"""
        self._evaluator = SafeEvaluator()

    @property
    def name(self) -> str:
        """工具名稱"""
        return "math_calculator"

    @property
    def description(self) -> str:
        """工具描述"""
        return "數學計算工具，支持基本數學運算、科學計算和安全的表達式求值"

    @property
    def version(self) -> str:
        """工具版本"""
        return "1.0.0"

    def _parse_expression(self, expression: str) -> ast.AST:
        """
        解析數學表達式

        Args:
            expression: 數學表達式字符串

        Returns:
            AST 節點

        Raises:
            ToolValidationError: 表達式解析失敗
        """
        try:
            # 使用 ast.parse 解析表達式
            tree = ast.parse(expression, mode="eval")
            return tree.body
        except SyntaxError as e:
            raise ToolValidationError(
                f"Invalid expression syntax: {str(e)}", field="expression"
            ) from e
        except Exception as e:
            raise ToolValidationError(
                f"Failed to parse expression: {str(e)}", field="expression"
            ) from e

    async def execute(self, input_data: MathInput) -> MathOutput:
        """
        執行數學計算

        Args:
            input_data: 工具輸入參數

        Returns:
            工具輸出結果

        Raises:
            ToolExecutionError: 工具執行失敗
            ToolValidationError: 輸入參數驗證失敗
        """
        try:
            # 解析表達式
            node = self._parse_expression(input_data.expression)

            # 安全求值
            result = self._evaluator.evaluate(node)

            logger.debug(
                "math_calculation_completed",
                expression=input_data.expression,
                result=result,
            )

            return MathOutput(result=result, expression=input_data.expression)

        except ToolValidationError:
            raise
        except Exception as e:
            logger.error("math_calculation_failed", error=str(e), exc_info=True)
            raise ToolExecutionError(
                f"Failed to calculate expression: {str(e)}", tool_name=self.name
            ) from e
