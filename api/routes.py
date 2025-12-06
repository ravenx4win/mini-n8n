"""API routes for workflow operations."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import uuid

from core.workflow import Workflow, WorkflowNode, WorkflowConnection
from core.registry import registry
from storage.database import get_database
from storage.models import ExecutionStatus
from storage.serialization import WorkflowSerializer
from executor.engine import WorkflowExecutor

router = APIRouter()

# Global executor instance
executor = WorkflowExecutor()


# Request/Response models

class CreateWorkflowRequest(BaseModel):
    """Request to create a new workflow."""
    name: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    connections: List[Dict[str, Any]] = Field(default_factory=list)


class UpdateWorkflowRequest(BaseModel):
    """Request to update a workflow."""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    connections: Optional[List[Dict[str, Any]]] = None


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow."""
    input_data: Dict[str, Any] = Field(default_factory=dict)
    use_cache: bool = True


class PreviewNodeRequest(BaseModel):
    """Request to preview a node execution."""
    type: str
    config: Dict[str, Any]
    inputs: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


# Workflow routes

@router.post("/workflows/", status_code=201)
async def create_workflow(request: CreateWorkflowRequest):
    """Create a new workflow.
    
    Args:
        request: Workflow creation request
        
    Returns:
        Created workflow data
    """
    try:
        # Create workflow object
        workflow = Workflow(
            name=request.name,
            description=request.description
        )
        
        # Add nodes
        for node_data in request.nodes:
            node = WorkflowNode(**node_data)
            workflow.add_node(node)
        
        # Add connections
        for conn_data in request.connections:
            conn = WorkflowConnection(**conn_data)
            workflow.add_connection(conn)
        
        # Validate workflow
        errors = workflow.validate_structure()
        if errors:
            raise HTTPException(status_code=400, detail=f"Invalid workflow: {', '.join(errors)}")
        
        # Save to database
        db = get_database()
        workflow_model = await db.create_workflow(workflow.to_dict())
        
        return workflow_model.data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a workflow by ID.
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        Workflow data
    """
    db = get_database()
    workflow_model = await db.get_workflow(workflow_id)
    
    if not workflow_model:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return workflow_model.data


@router.get("/workflows/")
async def list_workflows(limit: int = 100, offset: int = 0):
    """List all workflows.
    
    Args:
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        List of workflows
    """
    db = get_database()
    workflows = await db.list_workflows(limit=limit, offset=offset)
    
    return {
        "workflows": [w.data for w in workflows],
        "total": len(workflows)
    }


@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, request: UpdateWorkflowRequest):
    """Update a workflow.
    
    Args:
        workflow_id: Workflow ID
        request: Update request
        
    Returns:
        Updated workflow data
    """
    db = get_database()
    
    # Get existing workflow
    workflow_model = await db.get_workflow(workflow_id)
    if not workflow_model:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Update workflow
    workflow = Workflow.from_dict(workflow_model.data)
    
    if request.name is not None:
        workflow.name = request.name
    if request.description is not None:
        workflow.description = request.description
    if request.nodes is not None:
        workflow.nodes = [WorkflowNode(**n) for n in request.nodes]
    if request.connections is not None:
        workflow.connections = [WorkflowConnection(**c) for c in request.connections]
    
    workflow.version += 1
    
    # Validate
    errors = workflow.validate_structure()
    if errors:
        raise HTTPException(status_code=400, detail=f"Invalid workflow: {', '.join(errors)}")
    
    # Save
    updated_model = await db.update_workflow(workflow_id, workflow.to_dict())
    
    return updated_model.data


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow.
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        Success message
    """
    db = get_database()
    success = await db.delete_workflow(workflow_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {"message": "Workflow deleted successfully"}


# Execution routes

@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    background_tasks: BackgroundTasks
):
    """Execute a workflow.
    
    Args:
        workflow_id: Workflow ID
        request: Execution request
        background_tasks: Background task manager
        
    Returns:
        Execution ID and initial status
    """
    db = get_database()
    
    # Get workflow
    workflow_model = await db.get_workflow(workflow_id)
    if not workflow_model:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = Workflow.from_dict(workflow_model.data)
    
    # Create execution record
    execution_id = str(uuid.uuid4())
    await db.create_execution(
        execution_id=execution_id,
        workflow_id=workflow_id,
        input_data=request.input_data
    )
    
    # Execute workflow in background
    background_tasks.add_task(
        _execute_workflow_background,
        workflow,
        execution_id,
        request.input_data,
        request.use_cache
    )
    
    return {
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "status": "pending",
        "message": "Execution started"
    }


async def _execute_workflow_background(
    workflow: Workflow,
    execution_id: str,
    input_data: Dict[str, Any],
    use_cache: bool
):
    """Execute workflow in background."""
    from datetime import datetime
    
    db = get_database()
    
    try:
        # Update status to running
        await db.update_execution(
            execution_id=execution_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        # Execute workflow
        result = await executor.execute(
            workflow=workflow,
            input_data=input_data,
            use_cache=use_cache
        )
        
        # Update execution with result
        await db.update_execution(
            execution_id=execution_id,
            status=ExecutionStatus.SUCCESS if result.success else ExecutionStatus.FAILED,
            output_data=result.output,
            error=result.error,
            node_results=result.to_dict()["node_results"],
            execution_order=result.execution_order,
            finished_at=result.finished_at,
            execution_time=result.execution_time
        )
    
    except Exception as e:
        # Update execution with error
        await db.update_execution(
            execution_id=execution_id,
            status=ExecutionStatus.FAILED,
            error=str(e),
            finished_at=datetime.utcnow()
        )


@router.get("/workflows/{workflow_id}/executions/{execution_id}")
async def get_execution(workflow_id: str, execution_id: str):
    """Get execution results.
    
    Args:
        workflow_id: Workflow ID
        execution_id: Execution ID
        
    Returns:
        Execution data
    """
    db = get_database()
    
    execution = await db.get_execution(execution_id)
    
    if not execution or execution.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {
        "execution_id": execution.id,
        "workflow_id": execution.workflow_id,
        "status": execution.status.value,
        "input_data": execution.input_data,
        "output_data": execution.output_data,
        "error": execution.error,
        "node_results": execution.node_results,
        "execution_order": execution.execution_order,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
        "execution_time": execution.execution_time,
        "created_at": execution.created_at.isoformat()
    }


@router.get("/workflows/{workflow_id}/executions/")
async def list_executions(workflow_id: str, limit: int = 100, offset: int = 0):
    """List executions for a workflow.
    
    Args:
        workflow_id: Workflow ID
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        List of executions
    """
    db = get_database()
    executions = await db.list_executions(
        workflow_id=workflow_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "executions": [
            {
                "execution_id": e.id,
                "workflow_id": e.workflow_id,
                "status": e.status.value,
                "created_at": e.created_at.isoformat(),
                "execution_time": e.execution_time
            }
            for e in executions
        ],
        "total": len(executions)
    }


# Node type routes

@router.get("/node-types/")
async def list_node_types():
    """List all available node types.
    
    Returns:
        List of node type information
    """
    node_types = registry.list_all()
    
    return {
        "node_types": [
            {
                "type": info.type_name,
                "display_name": info.display_name,
                "description": info.description,
                "category": info.category,
                "config_schema": info.config_schema,
                "icon": info.icon
            }
            for info in node_types
        ],
        "categories": registry.get_categories()
    }


@router.get("/node-types/{type_name}")
async def get_node_type(type_name: str):
    """Get information about a specific node type.
    
    Args:
        type_name: Node type name
        
    Returns:
        Node type information
    """
    info = registry.get(type_name)
    
    if not info:
        raise HTTPException(status_code=404, detail="Node type not found")
    
    node_class = info.node_class
    
    return {
        "type": info.type_name,
        "display_name": info.display_name,
        "description": info.description,
        "category": info.category,
        "config_schema": info.config_schema,
        "input_schema": node_class.get_input_schema(),
        "output_schema": node_class.get_output_schema(),
        "icon": info.icon
    }


@router.post("/nodes/{type_name}/preview")
async def preview_node(type_name: str, request: PreviewNodeRequest):
    """Preview a node execution without saving.
    
    Args:
        type_name: Node type
        request: Preview request
        
    Returns:
        Node execution result
    """
    node_class = registry.get_class(type_name)
    
    if not node_class:
        raise HTTPException(status_code=404, detail="Node type not found")
    
    try:
        # Create node instance
        node = node_class(node_id="preview", config=request.config)
        
        # Execute
        result = await node.run(request.inputs, request.context)
        
        return {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
            "metadata": result.metadata
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Include router in app
from .app import app
app.include_router(router, prefix="/api/v1")


