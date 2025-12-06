"""
User Input Node - Captures user-provided data with validation, casting,
and metadata similar to Google Opal input nodes.
"""

from typing import Dict, Any, Optional
from .base import BaseNode, NodeResult


class UserInputNode(BaseNode):
    """
    Node for capturing and validating user input.
    Supports:
    - preset config values
    - runtime context values
    - default fallback
    - type validation
    - auto-casting
    """

    # ----------------------------------------
    # Main Logic
    # ----------------------------------------
    async def run(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> NodeResult:
        try:
            input_key = self.get_config_value("input_key", "value")
            required = self.get_config_value("required", True)
            expected_type = self.get_config_value("type", "text")

            # 1️⃣ Resolve value
            resolved_value, source = self._resolve_value(context, input_key)

            if resolved_value is None:
                if required:
                    msg = f"No value found for input key '{input_key}'"
                    return self.create_result(None, success=False, error=msg)
                else:
                    resolved_value = None

            # 2️⃣ Validate & cast
            try:
                resolved_value = self._validate_and_cast(resolved_value, expected_type)
            except ValueError as e:
                return self.create_result(None, success=False, error=str(e))

            # 3️⃣ Success metadata
            metadata = {
                "source": source,
                "input_key": input_key,
                "expected_type": expected_type,
                "original_value": resolved_value,
            }

            return self.create_result(
                output={"output": resolved_value, "value": resolved_value},
                success=True,
                **metadata
            )

        except Exception as e:
            self.log_error(f"Input node failed: {e}")
            return self.create_result(None, success=False, error=str(e))

    # ----------------------------------------
    # Value Resolver
    # ----------------------------------------
    def _resolve_value(self, context: Dict[str, Any], key: str):
        """Determine where the input value came from."""

        # 1. Pre-set value in config
        if "value" in self.config:
            return self.config["value"], "config"

        # 2. Runtime value in context
        if key in context:
            return context[key], "context"

        # 3. Default value
        if "default" in self.config:
            return self.config["default"], "default"

        return None, "missing"

    # ----------------------------------------
    # Validation & Casting
    # ----------------------------------------
    def _validate_and_cast(self, value: Any, expected_type: str):
        """Validate and cast input based on expected type."""

        if expected_type == "text":
            return str(value).strip()

        if expected_type == "number":
            try:
                return float(value) if "." in str(value) else int(value)
            except:
                raise ValueError(f"Expected number but got '{value}'")

        if expected_type == "boolean":
            if str(value).lower() in ("true", "1", "yes"):
                return True
            if str(value).lower() in ("false", "0", "no"):
                return False
            raise ValueError(f"Invalid boolean value: {value}")

        if expected_type == "json":
            if isinstance(value, (dict, list)):
                return value
            raise ValueError("Expected JSON object/array")

        return value

    # ----------------------------------------
    # Schema Definitions
    # ----------------------------------------
    @classmethod
    def get_input_schema(cls):
        return {
            "type": "object",
            "properties": {},
            "description": "User Input Node does not accept upstream inputs."
        }

    @classmethod
    def get_output_schema(cls):
        return {
            "type": "object",
            "properties": {
                "output": {"type": ["string", "number", "boolean", "object", "array"]},
                "value": {"type": ["string", "number", "boolean", "object", "array"]},
            },
            "required": ["output"]
        }

    @classmethod
    def get_config_schema(cls):
        return {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "UI prompt to display"
                },
                "input_key": {
                    "type": "string",
                    "default": "value",
                    "description": "Key to fetch from runtime context"
                },
                "value": {
                    "type": ["string", "number", "boolean", "object", "array"],
                    "description": "Predefined static value"
                },
                "default": {
                    "type": ["string", "number", "boolean", "object", "array"],
                    "description": "Fallback value if missing"
                },
                "required": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether input must be provided"
                },
                "type": {
                    "type": "string",
                    "enum": ["text", "number", "boolean", "json"],
                    "default": "text",
                    "description": "Expected input datatype"
                }
            }
        }
