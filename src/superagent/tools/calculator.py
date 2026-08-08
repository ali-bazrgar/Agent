from __future__ import annotations

import ast
import operator
from typing import Any

from superagent.tools.models import (
    RiskLevel,
    ToolCall,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolResult,
)
from superagent.tools.ports import ToolProvider


class CalculatorTool(ToolProvider):
    """Safe mathematical evaluator supporting basic arithmetic without eval()."""

    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="calculator",
            description="Safely evaluates basic mathematical arithmetic expressions.",
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression (e.g. '1847 * 392', '2 ** 10 + 5').",
                    }
                },
                "required": ["expression"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "result": {"type": "number"},
                    "expression": {"type": "string"},
                },
            },
            requires_network=False,
            risk_level=RiskLevel.LOW,
            timeout_seconds=2.0,
            enabled=True,
        )

    def execute(
        self,
        call: ToolCall,
        context: ToolExecutionContext | None = None,
    ) -> ToolResult:
        expr = call.arguments.get("expression") or call.arguments.get("formula")
        if not expr or not isinstance(expr, str) or not expr.strip():
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="calculator",
                status=ToolExecutionStatus.INVALID_ARGUMENTS,
                error="Argument 'expression' must be a non-empty string.",
            )

        expr_clean = expr.strip()

        try:
            val = self._evaluate_expression(expr_clean)
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="calculator",
                status=ToolExecutionStatus.SUCCESS,
                output={"result": val, "expression": expr_clean},
            )
        except ZeroDivisionError:
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="calculator",
                status=ToolExecutionStatus.ERROR,
                error="Division by zero.",
            )
        except Exception as exc:
            return ToolResult(
                tool_call_id=call.tool_call_id,
                tool_name="calculator",
                status=ToolExecutionStatus.SECURITY_REJECTED
                if "Unsupported" in str(exc) or "Syntax" in str(exc)
                else ToolExecutionStatus.ERROR,
                error=f"Invalid or unsafe math expression: {exc}",
            )

    def _evaluate_expression(self, expr: str) -> float | int:
        parsed = ast.parse(expr, mode="eval")
        return self._eval_node(parsed.body)

    def _eval_node(self, node: ast.AST) -> float | int:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
            # Prevent excessive power computation
            if op_type == ast.Pow and (right > 100 or left > 10000):
                raise ValueError("Exponent or base too large")
            return self._OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type not in self._OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            return self._OPERATORS[op_type](operand)
        else:
            raise ValueError(f"Unsupported AST node type: {type(node).__name__}")
