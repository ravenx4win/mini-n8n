"""
Conditional Logic Node - Advanced IF/ELSE branching (Opal-grade)
"""

from typing import Dict, Any, List
from .base import BaseNode
from utils.template import interpolate_variables
import json


class ConditionalLogicNode(BaseNode):
    """
    Supports:
    - Single condition evaluation
    - Multiple conditions
    - AND / OR combination logic
    - Automatic type detection
    - Boolean / numeric / text comparisons
    - Contains, starts_with, ends_with
    - is_empty / is_not_empty
    """

    async def run(self, inputs: Dict[str, Any], context: Dict[str, Any]):
        try:
            conditions: List[Dict[str, Any]] = self.get_config_value("conditions", [])
            logic_mode = self.get_config_value("logic_mode", "AND").upper()

            evaluated_conditions = []
            results = []

            # -----------------------------------------------------
            # 1) Evaluate each condition
            # -----------------------------------------------------
            for cond in conditions:
                value1_raw = interpolate_variables(str(cond.get("value1", "")), context, inputs)
                value2_raw = interpolate_variables(str(cond.get("value2", "")), context, inputs)

                value1 = self._parse_value(value1_raw)
                value2 = self._parse_value(value2_raw)

                condition_type = cond.get("condition_type", "equals")

                passed = self._evaluate_condition(condition_type, value1, value2)

                evaluated_conditions.append({
                    "value1": value1,
                    "value2": value2,
                    "condition_type": condition_type,
                    "result": passed
                })

                results.append(passed)

            # -----------------------------------------------------
            # 2) Apply logic mode (AND / OR)
            # -----------------------------------------------------
            if logic_mode == "AND":
                final_result = all(results)
            elif logic_mode == "OR":
                final_result = any(results)
            else:
                final_result = False

            branch = "true" if final_result else "false"

            self.log_info(f"Conditional result: {final_result} → branch '{branch}'")

            return self.create_result(
                output={
                    "result": final_result,
                    "output": final_result,
                    "branch": branch,
                    "evaluated": evaluated_conditions,
                    "logic_mode": logic_mode
                },
                success=True
            )

        except Exception as e:
            self.log_error(f"ConditionalNode error: {e}")
            return self.create_result(None, success=False, error=str(e))

    # =====================================================================
    # Value Parsing (Safe + Strong Typed)
    # =====================================================================
    def _parse_value(self, value_raw: str):
        """Convert strings into booleans, numbers, JSON, or keep as string."""

        # Boolean
        if value_raw.lower() == "true":
            return True
        if value_raw.lower() == "false":
            return False

        # Null
        if value_raw.lower() in ("null", "none"):
            return None

        # Number (int/float)
        try:
            if "." in value_raw:
                return float(value_raw)
            return int(value_raw)
        except ValueError:
            pass

        # JSON object/list
        try:
            return json.loads(value_raw)
        except Exception:
            pass

        # Fallback to string
        return value_raw

    # =====================================================================
    # Condition Evaluation
    # =====================================================================
    def _evaluate_condition(self, condition_type: str, value1: Any, value2: Any) -> bool:
        try:
            if condition_type == "equals":
                return value1 == value2

            if condition_type == "not_equals":
                return value1 != value2

            if condition_type == "greater_than":
                return self._safe_compare(value1, value2, lambda a, b: a > b)

            if condition_type == "less_than":
                return self._safe_compare(value1, value2, lambda a, b: a < b)

            if condition_type == "greater_or_equal":
                return self._safe_compare(value1, value2, lambda a, b: a >= b)

            if condition_type == "less_or_equal":
                return self._safe_compare(value1, value2, lambda a, b: a <= b)

            if condition_type == "contains":
                return str(value2) in str(value1)

            if condition_type == "not_contains":
                return str(value2) not in str(value1)

            if condition_type == "starts_with":
                return str(value1).startswith(str(value2))

            if condition_type == "ends_with":
                return str(value1).endswith(str(value2))

            if condition_type == "is_empty":
                return value1 in ("", None, [], {}) or (isinstance(value1, str) and value1.strip() == "")

            if condition_type == "is_not_empty":
                return not (value1 in ("", None, [], {}) or (isinstance(value1, str) and value1.strip() == ""))

            raise ValueError(f"Unknown condition type: {condition_type}")

        except Exception as e:
            self.log_warning(f"Condition evaluation failed: {e}")
            return False

    def _safe_compare(self, a, b, op):
        """Prevent type errors when comparing numbers/strings."""
        try:
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                return op(a, b)
            # Try converting both to float
            return op(float(a), float(b))
        except Exception:
            return False

    # =====================================================================
    # SCHEMAS
    # =====================================================================
    @classmethod
    def get_input_schema(cls):
        return {
            "type": "object",
            "properties": {
                "value1": {"type": ["string", "number", "boolean"]},
                "value2": {"type": ["string", "number", "boolean"]},
            }
        }

    @classmethod
    def get_output_schema(cls):
        return {
            "type": "object",
            "properties": {
                "result": {"type": "boolean"},
                "branch": {"type": "string", "enum": ["true", "false"]},
                "evaluated": {"type": "array"},
                "logic_mode": {"type": "string"},
            },
            "required": ["result", "branch"]
        }

    @classmethod
    def get_config_schema(cls):
        return {
            "type": "object",
            "properties": {
                "logic_mode": {
                    "type": "string",
                    "enum": ["AND", "OR"],
                    "default": "AND",
                    "description": "If multiple conditions exist, how should they be combined?"
                },
                "conditions": {
                    "type": "array",
                    "description": "List of conditions",
                    "items": {
                        "type": "object",
                        "properties": {
                            "condition_type": {
                                "type": "string",
                                "enum": [
                                    "equals",
                                    "not_equals",
                                    "greater_than",
                                    "less_than",
                                    "greater_or_equal",
                                    "less_or_equal",
                                    "contains",
                                    "not_contains",
                                    "starts_with",
                                    "ends_with",
                                    "is_empty",
                                    "is_not_empty"
                                ],
                                "default": "equals"
                            },
                            "value1": {"type": "string"},
                            "value2": {"type": "string"},
                        },
                        "required": ["condition_type", "value1"]
                    }
                }
            },
            "required": ["conditions"]
        }
