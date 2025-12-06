"""Workflow execution engine with dependency resolution and error handling."""

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


@dataclass
class ExecutionContext:
    """Context for workflow execution."""
    
    workflow_id: str
    execution_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    node_outputs: Dict[str, Any] = field(default_factory=dict)
    use_cache: bool = True


@dataclass
class ExecutionResult:
    """Result of workflow execution."""
    
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
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "node_results": {
                node_id: {
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                    "execution_time": result.execution_time,
                    "metadata": result.metadata
                }
                for node_id, result in self.node_results.items()
            },
            "execution_order": self.execution_order,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "execution_time": self.execution_time
        }


class WorkflowExecutor:
    """Execute workflows with dependency resolution and caching."""
    
    def __init__(self, cache: Optional[ExecutionCache] = None):
        """Initialize executor.
        
        Args:
            cache: Optional execution cache
        """
        self.cache = cache or ExecutionCache()
        self.logger = logging.getLogger(__name__)
    
    async def execute(
        self,
        workflow: Workflow,
        input_data: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> ExecutionResult:
        """Execute a workflow.
        
        Args:
            workflow: Workflow to execute
            input_data: Input data for the workflow
            use_cache: Whether to use caching
            
        Returns:
            ExecutionResult with output or error
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Create execution context
        context = ExecutionContext(
            workflow_id=workflow.id,
            execution_id=execution_id,
            input_data=input_data or {},
            variables=input_data or {},
            use_cache=use_cache
        )
        
        result = ExecutionResult(
            execution_id=execution_id,
            workflow_id=workflow.id,
            success=False,
            started_at=datetime.utcnow()
        )
        
        try:
            self.logger.info(f"Starting execution {execution_id} for workflow {workflow.id}")
            
            # Validate workflow structure
            errors = workflow.validate_structure()
            if errors:
                raise ValueError(f"Invalid workflow structure: {', '.join(errors)}")
            
            # Build DAG from workflow
            dag = self._build_dag(workflow)
            
            # Get execution order
            execution_order = TopologicalSorter.sort(dag)
            result.execution_order = execution_order
            
            self.logger.info(f"Execution order: {execution_order}")
            
            # Execute nodes in order
            for node_id in execution_order:
                node = workflow.get_node(node_id)
                if not node:
                    raise ValueError(f"Node not found: {node_id}")
                
                # Execute node
                node_result = await self._execute_node(node, workflow, context)
                result.node_results[node_id] = node_result
                
                # Check for errors
                if not node_result.success:
                    error_msg = f"Node {node_id} failed: {node_result.error}"
                    self.logger.error(error_msg)
                    result.error = error_msg
                    result.success = False
                    break
                
                # Store node output in context
                context.node_outputs[node_id] = node_result.output
            
            # If all nodes succeeded, extract final output
            if not result.error:
                result.output = self._extract_output(workflow, context)
                result.success = True
                self.logger.info(f"Execution {execution_id} completed successfully")
            
        except CycleDetectedError as e:
            error_msg = f"Cycle detected in workflow: {e}"
            self.logger.error(error_msg)
            result.error = error_msg
            result.success = False
        
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result.error = error_msg
            result.success = False
        
        finally:
            result.finished_at = datetime.utcnow()
            result.execution_time = time.time() - start_time
            self.logger.info(
                f"Execution {execution_id} finished in {result.execution_time:.2f}s"
            )
        
        return result
    
    def _build_dag(self, workflow: Workflow) -> DAG:
        """Build DAG from workflow connections.
        
        Args:
            workflow: Workflow to build DAG from
            
        Returns:
            DAG representing workflow structure
        """
        dag = DAG()
        
        # Add all nodes
        for node in workflow.nodes:
            dag.add_node(node.id)
        
        # Add connections as edges
        for conn in workflow.connections:
            dag.add_edge(conn.from_node, conn.to_node)
        
        return dag
    
    async def _execute_node(
        self,
        node,
        workflow: Workflow,
        context: ExecutionContext
    ) -> NodeResult:
        """Execute a single node.
        
        Args:
            node: Node to execute
            workflow: Parent workflow
            context: Execution context
            
        Returns:
            NodeResult
        """
        node_id = node.id
        node_type = node.type
        node_config = node.config
        
        try:
            self.logger.info(f"Executing node {node_id} ({node_type})")
            
            # Collect inputs from connected nodes
            node_inputs = self._collect_node_inputs(node_id, workflow, context)
            
            # Check cache
            if context.use_cache:
                cached_result = self.cache.get(node_type, node_config, node_inputs)
                if cached_result is not None:
                    self.logger.info(f"Using cached result for node {node_id}")
                    return cached_result
            
            # Create node instance
            node_class = registry.get_class(node_type)
            if not node_class:
                raise ValueError(f"Unknown node type: {node_type}")
            
            node_instance = node_class(node_id=node_id, config=node_config)
            
            # Validate configuration
            config_errors = node_instance.validate_config()
            if config_errors:
                raise ValueError(f"Invalid configuration: {', '.join(config_errors)}")
            
            # Execute node
            start_time = time.time()
            result = await node_instance.run(node_inputs, context.variables)
            result.execution_time = time.time() - start_time
            
            # Cache result if successful
            if result.success and context.use_cache:
                self.cache.set(node_type, node_config, node_inputs, result)
            
            self.logger.info(
                f"Node {node_id} executed in {result.execution_time:.2f}s"
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error executing node {node_id}: {e}", exc_info=True)
            return NodeResult(
                success=False,
                output=None,
                error=str(e)
            )
    
    def _collect_node_inputs(
        self,
        node_id: str,
        workflow: Workflow,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Collect inputs for a node from connected nodes.
        
        Args:
            node_id: Node ID
            workflow: Parent workflow
            context: Execution context
            
        Returns:
            Dictionary of inputs
        """
        inputs = {}
        
        # Get incoming connections
        incoming = workflow.get_node_inputs(node_id)
        
        for conn in incoming:
            source_node_id = conn.from_node
            from_output = conn.from_output
            to_input = conn.to_input
            
            # Get output from source node
            if source_node_id in context.node_outputs:
                source_output = context.node_outputs[source_node_id]
                
                # Extract specific output key
                if isinstance(source_output, dict) and from_output in source_output:
                    value = source_output[from_output]
                else:
                    value = source_output
                
                inputs[to_input] = value
                inputs[source_node_id] = source_output
        
        return inputs
    
    def _extract_output(
        self,
        workflow: Workflow,
        context: ExecutionContext
    ) -> Any:
        """Extract final output from workflow execution.
        
        Args:
            workflow: Executed workflow
            context: Execution context
            
        Returns:
            Final output
        """
        # Find output nodes
        output_nodes = [
            node for node in workflow.nodes
            if node.type == "output"
        ]
        
        if output_nodes:
            # Use first output node
            output_node_id = output_nodes[0].id
            if output_node_id in context.node_outputs:
                return context.node_outputs[output_node_id]
        
        # No output node, return all outputs
        return context.node_outputs


