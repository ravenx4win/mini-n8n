"""
Workflow Execution Engine (Mode A - Simple, Linear, Clean)
Executes workflows using DAG ordering, resolves dependencies,
runs nodes, handles errors, and stores results.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import time
import logging
import uuid

from core.workflow import Workflow
from core.dag import DAG, TopologicalSorter, CycleDetectedError
from core.registry import registry
from nodes.base import NodeResult
from .cache import ExecutionCache

logger = logging.getLogger(__name__)


# =====================================================================
# Execution Context
# =====================================================================
@dataclass
class ExecutionContext:
    """Holds data shared during workflow execution."""

    workflow_id: str
    execution_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    node_outputs: Dict[str, Any] = field(default_factory=dict)
    use_cache: bool = True


# =====================================================================
# Execution Result
# =====================================================================
@dataclass
class ExecutionResult:
    """Final result returned after workflow execution."""

    execution_id: str
    workflow_id: str
    success: bool
    output: Optional[Any] = None
    error: Optional[str] = None
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "node_results": {
                node_id: {
                    "success": res.success,
                    "output": res.output,
                    "error": res.error,
                    "execution_time": res.execution_time,
                    "metadata": res.metadata,
                }
                for node_id, res in self.node_results.items()
            },
            "execution_order": self.execution_order,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "execution_time": self.execution_time,
        }


# =====================================================================
# Workflow Executor (Mode A)
# =====================================================================
class WorkflowExecutor:
    """Executes workflows in simple DAG-based linear order."""

    def __init__(self, cache: Optional[ExecutionCache] = None):
        self.cache = cache or ExecutionCache()
        self.logger = logging.getLogger(__name__)

    # -----------------------------------------------------------------
    # MAIN EXECUTION ENTRY POINT
    # -----------------------------------------------------------------
    async def execute(
        self,
        workflow: Workflow,
        input_data: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> ExecutionResult:

        execution_id = str(uuid.uuid4())
        start_time = time.time()

        context = ExecutionContext(
            workflow_id=workflow.id,
            execution_id=execution_id,
            input_data=input_data or {},
            variables=input_data or {},
            use_cache=use_cache,
        )

        result = ExecutionResult(
            execution_id=execution_id,
            workflow_id=workflow.id,
            success=False,
            started_at=datetime.utcnow(),
        )

        try:
            self.logger.info(f"Starting workflow execution {execution_id}")

            # -----------------------------
            # Validate workflow
            # -----------------------------
            errors = workflow.validate_structure()
            if errors:
                raise ValueError(", ".join(errors))

            # -----------------------------
            # Build DAG and determine order
            # -----------------------------
            dag = self._build_dag(workflow)
            order = TopologicalSorter.sort(dag)
            result.execution_order = order

            # -----------------------------
            # Execute nodes sequentially
            # -----------------------------
            for node_id in order:
                node = workflow.get_node(node_id)
                if not node:
                    raise ValueError(f"Missing node: {node_id}")

                node_result = await self._execute_node(node, workflow, context)
                result.node_results[node_id] = node_result

                # Stop on failure
                if not node_result.success:
                    result.error = f"Node {node_id} failed: {node_result.error}"
                    break

                context.node_outputs[node_id] = node_result.output

            # -----------------------------
            # Final output
            # -----------------------------
            if not result.error:
                result.output = self._extract_output(workflow, context)
                result.success = True

        except CycleDetectedError as e:
            result.error = f"CycleDetectedError: {str(e)}"
            result.success = False

        except Exception as e:
            result.error = f"ExecutionError: {str(e)}"
            result.success = False

        finally:
            result.finished_at = datetime.utcnow()
            result.execution_time = time.time() - start_time
            self.logger.info(f"Workflow finished in {result.execution_time:.2f}s")

        return result

    # =================================================================
    # DAG Construction
    # =================================================================
    def _build_dag(self, workflow: Workflow) -> DAG:
        dag = DAG()

        for node in workflow.nodes:
            dag.add_node(node.id)

        for c in workflow.connections:
            dag.add_edge(c.from_node, c.to_node)

        return dag

    # =================================================================
    # Execute a Single Node
    # =================================================================
    async def _execute_node(self, node, workflow: Workflow, context: ExecutionContext):
        node_id = node.id
        node_type = node.type
        node_config = node.config

        try:
            self.logger.info(f"Running node {node_id} ({node_type})")

            # Collect inputs
            node_inputs = self._collect_inputs(node_id, workflow, context)

            # Cache lookup
            if context.use_cache:
                cached = self.cache.get(node_type, node_config, node_inputs)
                if cached:
                    return cached

            # Instantiate node
            node_class = registry.get_class(node_type)
            if not node_class:
                raise ValueError(f"Unregistered node type: {node_type}")

            instance = node_class(node_id=node_id, config=node_config)

            # Validate config
            errs = instance.validate_config()
            if errs:
                raise ValueError(", ".join(errs))

            # Execute
            start = time.time()
            result: NodeResult = await instance.run(node_inputs, context.variables)
            result.execution_time = time.time() - start

            # Save to cache
            if result.success and context.use_cache:
                self.cache.set(node_type, node_config, node_inputs, result)

            return result

        except Exception as e:
            return NodeResult(success=False, output=None, error=str(e))

    # =================================================================
    # Gather inputs from previous nodes
    # =================================================================
    def _collect_inputs(self, node_id: str, workflow: Workflow, context: ExecutionContext):
        inputs = {}
        incoming = workflow.get_node_inputs(node_id)

        for conn in incoming:
            src = conn.from_node
            output_key = conn.from_output
            input_key = conn.to_input

            if src in context.node_outputs:
                src_output = context.node_outputs[src]

                # If dict and specific output key exists
                if isinstance(src_output, dict) and output_key in src_output:
                    val = src_output[output_key]
                else:
                    val = src_output

                inputs[input_key] = val
                inputs[src] = src_output

        return inputs

    # =================================================================
    # Extract final workflow output
    # =================================================================
    def _extract_output(self, workflow: Workflow, context: ExecutionContext):
        output_nodes = [n for n in workflow.nodes if n.type == "output"]
        if output_nodes:
            out_id = output_nodes[0].id
            return context.node_outputs.get(out_id)

        # If no explicit output node → return everything
        return context.node_outputs
