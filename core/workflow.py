"""
Workflow data structures and execution engine.

This file contains:
- Workflow data models (WorkflowNode, WorkflowConnection, Workflow)
- WorkflowRunner: DAG-driven executor that runs workflows using the Node Registry + DAG
  and returns structured run results.

Notes:
- Nodes are instantiated using the global `registry` (core.registry.registry).
- DAG ordering and parallelism use TopologicalSorter from core.dag.
- Each node is executed via its BaseNode.execute(...) wrapper (ensures timing, errors, metadata).
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone
import uuid
import asyncio
import time
import logging

from core.dag import DAG, TopologicalSorter, CycleDetectedError, DAGValidationError
from core.registry import registry, NodeTypeInfo
from . import registry as _unused_registry_import  # ensures package resolution in some setups
from nodes.base import NodeResult, BaseNode  # type: ignore

logger = logging.getLogger(__name__)


# -----------------------
# Data Models (Workflow)
# -----------------------

class WorkflowConnection(BaseModel):
    """Represents a connection between two nodes in a workflow."""

    from_node: str = Field(..., description="Source node ID")
    to_node: str = Field(..., description="Destination node ID")
    from_output: str = Field(default="output", description="Output key from source node")
    to_input: str = Field(default="input", description="Input key for destination node")


class WorkflowNode(BaseModel):
    """Represents a single node in a workflow."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique node ID")
    type: str = Field(..., description="Node type (e.g., 'llm_text_generation')")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node configuration")
    position: Optional[Dict[str, float]] = Field(default=None, description="Visual position for frontend")
    name: Optional[str] = Field(default=None, description="Human-readable node name")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if self.name is None:
            self.name = f"{self.type}_{self.id[:8]}"


class Workflow(BaseModel):
    """Represents a complete workflow with nodes and connections."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique workflow ID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    nodes: List[WorkflowNode] = Field(default_factory=list, description="List of nodes")
    connections: List[WorkflowConnection] = Field(default_factory=list, description="List of connections")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, description="Workflow version")

    # ---------------------------
    # Convenience accessors
    # ---------------------------
    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def add_node(self, node: WorkflowNode) -> None:
        self.nodes.append(node)
        self.updated_at = datetime.now(timezone.utc)

    def remove_node(self, node_id: str) -> bool:
        if self.get_node(node_id) is None:
            return False
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.connections = [c for c in self.connections if c.from_node != node_id and c.to_node != node_id]
        self.updated_at = datetime.now(timezone.utc)
        return True

    def add_connection(self, connection: WorkflowConnection) -> None:
        self.connections.append(connection)
        self.updated_at = datetime.now(timezone.utc)

    def get_node_inputs(self, node_id: str) -> List[WorkflowConnection]:
        return [c for c in self.connections if c.to_node == node_id]

    def get_node_outputs(self, node_id: str) -> List[WorkflowConnection]:
        return [c for c in self.connections if c.from_node == node_id]

    def validate_structure(self) -> List[str]:
        errors: List[str] = []
        node_ids = {node.id for node in self.nodes}
        for conn in self.connections:
            if conn.from_node not in node_ids:
                errors.append(f"Connection references non-existent node: {conn.from_node}")
            if conn.to_node not in node_ids:
                errors.append(f"Connection references non-existent node: {conn.to_node}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        return cls(**data)


# -----------------------
# Workflow Runner
# -----------------------

class WorkflowRunError(Exception):
    """Raised when a workflow run fails in a non-node specific way."""
    pass


class WorkflowRunner:
    """
    Execute a Workflow instance.

    Behavior summary:
    - Build DAG from workflow connections
    - Validate structure
    - Instantiate nodes from registry
    - Execute nodes per topological levels (parallel within a level)
    - Map outputs from source nodes to destination node inputs by connection mapping
    - Collect NodeResult for each node and return a comprehensive run result

    Usage:
        runner = WorkflowRunner(workflow)
        results = await runner.run(context={"user": {...}})
    """

    def __init__(
        self,
        workflow: Workflow,
        concurrency_limit: Optional[int] = None,
        per_node_timeout: Optional[float] = None,
    ):
        self.workflow = workflow
        self.concurrency_limit = concurrency_limit or 0  # 0 => no semaphore
        self.per_node_timeout = per_node_timeout  # seconds (optional)
        self._node_instances: Dict[str, BaseNode] = {}
        self._results: Dict[str, NodeResult] = {}
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None

    # ---------------------------
    # Public runner API
    # ---------------------------
    async def run(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the workflow asynchronously.

        Returns a dictionary with:
        - workflow_id, run_id, start_time, end_time, duration_seconds
        - status ("success" or "failed")
        - node_results: mapping node_id -> NodeResult.model-like dict
        - errors: list of error messages (if any)
        """
        run_id = str(uuid.uuid4())
        self._start_time = time.time()
        start_dt = datetime.now(timezone.utc)

        # Validate workflow structure (quick checks)
        struct_errors = self.workflow.validate_structure()
        if struct_errors:
            raise WorkflowRunError(f"Workflow structure invalid: {struct_errors}")

        # Build DAG
        dag = DAG()
        for node in self.workflow.nodes:
            dag.add_node(node.id)
        for conn in self.workflow.connections:
            dag.add_edge(conn.from_node, conn.to_node)

        # Validate DAG (detect cycles)
        try:
            dag.validate()
        except (CycleDetectedError, DAGValidationError) as e:
            raise WorkflowRunError(f"DAG validation failed: {e}")

        # Instantiate nodes from registry
        try:
            self._instantiate_nodes()
        except Exception as e:
            raise WorkflowRunError(f"Failed to instantiate nodes: {e}")

        # Build execution levels
        levels = TopologicalSorter.execution_levels(dag)

        # Prepare runtime context
        context: Dict[str, Any] = {"workflow": {"id": self.workflow.id, "name": self.workflow.name}}
        if initial_context:
            context.update(initial_context)
        context["run_id"] = run_id
        context["started_at"] = start_dt.isoformat()

        errors: List[str] = []

        # Optional concurrency semaphore (global per level)
        semaphore = asyncio.Semaphore(self.concurrency_limit) if self.concurrency_limit > 0 else None

        # Execute each level sequentially; nodes in level can run concurrently
        for level in levels:
            tasks = []
            for node_id in level:
                coro = self._execute_node(node_id, context, semaphore)
                # If per-node timeout set, wrap with asyncio.wait_for
                if self.per_node_timeout:
                    coro = asyncio.wait_for(coro, timeout=self.per_node_timeout)
                tasks.append(asyncio.create_task(coro))

            # Wait for all tasks in this level to finish (gather),
            # but don't cancel remaining nodes on a single failure; we collect errors
            level_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Inspect results and collect errors
            for idx, res in enumerate(level_results):
                if isinstance(res, Exception):
                    node_id = level[idx]
                    err_msg = f"Node {node_id} execution error: {res}"
                    logger.exception(err_msg)
                    errors.append(err_msg)
                    # ensure there is a NodeResult entry for failed node
                    if node_id not in self._results:
                        self._results[node_id] = NodeResult(
                            success=False,
                            output=None,
                            error=str(res),
                            execution_time=0.0,
                            metadata={"node_id": node_id}
                        )

            # If you want to abort all on first level error, uncomment:
            # if errors:
            #     break

        self._end_time = time.time()
        end_dt = datetime.now(timezone.utc)
        duration = (self._end_time - self._start_time) if self._start_time else None

        # Build serializable results
        node_results_serializable = {
            nid: {
                "success": r.success,
                "output": r.output,
                "error": r.error,
                "execution_time": r.execution_time,
                "metadata": r.metadata
            }
            for nid, r in self._results.items()
        }

        overall_status = "failed" if any(not r.success for r in self._results.values()) or errors else "success"

        return {
            "workflow_id": self.workflow.id,
            "workflow_name": self.workflow.name,
            "run_id": run_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "duration_seconds": duration,
            "status": overall_status,
            "node_results": node_results_serializable,
            "errors": errors,
        }

    # ---------------------------
    # Internals
    # ---------------------------
    def _instantiate_nodes(self) -> None:
        """Instantiate node classes from the registry for each WorkflowNode."""
        for wnode in self.workflow.nodes:
            node_cls = registry.get_class(wnode.type)
            if node_cls is None:
                raise WorkflowRunError(f"Node type not registered: {wnode.type} (node id: {wnode.id})")
            # create instance via constructor signature (node_id, config)
            instance = registry.create_instance(wnode.type, node_id=wnode.id, config=wnode.config)
            self._node_instances[wnode.id] = instance

    async def _execute_node(self, node_id: str, context: Dict[str, Any], semaphore: Optional[asyncio.Semaphore]) -> NodeResult:
        """
        Execute a single node: collect inputs from previous nodes (per connections),
        call node.execute(inputs, context) and store NodeResult in self._results.
        """
        if semaphore:
            async with semaphore:
                return await self._run_node_and_store(node_id, context)
        else:
            return await self._run_node_and_store(node_id, context)

    async def _run_node_and_store(self, node_id: str, context: Dict[str, Any]) -> NodeResult:
        """Collect inputs, run node.execute and store result in self._results."""

        wnode = self.workflow.get_node(node_id)
        if wnode is None:
            raise WorkflowRunError(f"Internal error: workflow node {node_id} not found during execution")

        # Build input payload to node: gather all incoming connections and map outputs
        incoming_conns = self.workflow.get_node_inputs(node_id)
        node_inputs: Dict[str, Any] = {}

        for conn in incoming_conns:
            src_id = conn.from_node
            # If source didn't run or has no result yet, value becomes None
            src_result = self._results.get(src_id)
            if src_result and src_result.success:
                # prefer structured output keys
                if isinstance(src_result.output, dict):
                    node_inputs[conn.to_input] = src_result.output.get(conn.from_output)
                else:
                    # If output is primitive, map to the configured output key only when name matches
                    node_inputs[conn.to_input] = src_result.output if conn.from_output == "output" else None
            else:
                # missing source or failed -> None (node implementations should handle missing gracefully)
                node_inputs[conn.to_input] = None

        # Also allow upstream "raw" keys when inputs are named by node id -> pass entire source output under key src_id
        # (Some UIs expect inputs to contain other nodes' outputs directly)
        # Map: node_inputs["_sources"][src_id] = src_result.output
        node_inputs["_sources"] = {src: (self._results[src].output if src in self._results else None) for src in [c.from_node for c in incoming_conns]}

        # If node expects an "input" default and there is a single unnamed input, copy it
        if "input" not in node_inputs and len(node_inputs) == 1:
            # don't change anything — keep as-is
            pass

        # Add runtime context copy (nodes may mutate context if needed)
        runtime_context = dict(context)

        # Execute node instance (ensure we call the BaseNode.execute wrapper)
        node_instance: BaseNode = self._node_instances[node_id]

        try:
            # BaseNode.execute returns NodeResult (safe wrapper)
            result: NodeResult = await node_instance.execute(node_inputs, runtime_context)

            # If node's run() returned raw NodeResult-like dict, adapt here (rare)
            if not isinstance(result, NodeResult):
                # wrap into NodeResult (best-effort)
                result = NodeResult(success=True, output=result, error=None, execution_time=0.0, metadata={"node_id": node_id})

        except Exception as e:
            logger.exception(f"Exception while running node {node_id}: {e}")
            result = NodeResult(success=False, output=None, error=str(e), execution_time=0.0, metadata={"node_id": node_id})

        # Enrich metadata with node id and type
        result.metadata.setdefault("node_id", node_id)
        result.metadata.setdefault("node_type", self.workflow.get_node(node_id).type if self.workflow.get_node(node_id) else "unknown")

        # Persist result
        self._results[node_id] = result
        return result

    # ---------------------------
    # Convenience (sync wrapper)
    # ---------------------------
    def run_sync(self, initial_context: Optional[Dict[str, Any]] = None, loop: Optional[asyncio.AbstractEventLoop] = None) -> Dict[str, Any]:
        """Synchronous wrapper for convenience / scripts."""
        loop = loop or asyncio.get_event_loop()
        return loop.run_until_complete(self.run(initial_context=initial_context))


# -----------------------
# Module-level helper
# -----------------------

async def run_workflow_async(workflow: Workflow, initial_context: Optional[Dict[str, Any]] = None, concurrency_limit: Optional[int] = None, per_node_timeout: Optional[float] = None) -> Dict[str, Any]:
    runner = WorkflowRunner(workflow, concurrency_limit=concurrency_limit or 0, per_node_timeout=per_node_timeout)
    return await runner.run(initial_context=initial_context)


def run_workflow(workflow: Workflow, initial_context: Optional[Dict[str, Any]] = None, concurrency_limit: Optional[int] = None, per_node_timeout: Optional[float] = None) -> Dict[str, Any]:
    runner = WorkflowRunner(workflow, concurrency_limit=concurrency_limit or 0, per_node_timeout=per_node_timeout)
    return runner.run_sync(initial_context=initial_context)
