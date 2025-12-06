"""
Base node class that all node types inherit from.
Includes:
- Async-safe execution
- Automatic timing
- Error handling
- Config + schema validation
- Lifecycle hooks
- Metadata tracking
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
import time
import inspect


logger = logging.getLogger(__name__)


class NodeExecutionError(Exception):
    """Raised when a node fails to execute."""
    pass


@dataclass
class NodeResult:
    """Result of node execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseNode(ABC):
    """Base class for all workflow nodes."""

    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ----------------------------------------
    # Lifecycle Hooks
    # ----------------------------------------
    async def before_run(self, inputs: Dict[str, Any], context: Dict[str, Any]):
        """Hook before executing the node."""
        self.log_info("Starting execution.", inputs=inputs)

    async def after_run(self, result: NodeResult):
        """Hook after executing the node."""
        self.log_info(
            "Execution finished.",
            success=result.success,
            time=result.execution_time
        )

    # ----------------------------------------
    # Main Execution Wrapper
    # ----------------------------------------
    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> NodeResult:
        """Safe async wrapper around run() that handles:
        - timing
        - errors
        - lifecycle hooks
        - metadata enrichment
        """

        await self.before_run(inputs, context)

        start_time = time.time()
        try:
            # Support async + sync run() methods
            if inspect.iscoroutinefunction(self.run):
                output = await self.run(inputs, context)
            else:
                output = self.run(inputs, context)

            execution_time = time.time() - start_time

            result = NodeResult(
                success=True,
                output=output,
                execution_time=execution_time,
                metadata={
                    "node_id": self.node_id,
                    "node_type": self.__class__.__name__,
                }
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.log_error(f"Execution failed: {str(e)}")

            result = NodeResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=execution_time,
                metadata={
                    "node_id": self.node_id,
                    "node_type": self.__class__.__name__,
                }
            )

        await self.after_run(result)
        return result

    # ----------------------------------------
    # Methods nodes MUST implement
    # ----------------------------------------
    @abstractmethod
    async def run(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Any:
        pass

    @classmethod
    @abstractmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        return {}

    @classmethod
    @abstractmethod
    def get_output_schema(cls) -> Dict[str, Any]:
        return {}

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {}

    # ----------------------------------------
    # Config Validation
    # ----------------------------------------
    def validate_config(self):
        errors = []
        schema = self.get_config_schema()
        required = schema.get("required", [])

        for field in required:
            if field not in self.config:
                errors.append(f"Missing required config: {field}")

        return errors

    # ----------------------------------------
    # Helpers
    # ----------------------------------------
    def get_config_value(self, key: str, default: Any = None):
        return self.config.get(key, default)

    def log_info(self, message: str, **kwargs):
        self.logger.info(f"[{self.node_id}] {message} | {kwargs}")

    def log_error(self, message: str, **kwargs):
        self.logger.error(f"[{self.node_id}] {message} | {kwargs}")

    def log_warning(self, message: str, **kwargs):
        self.logger.warning(f"[{self.node_id}] {message} | {kwargs}")
