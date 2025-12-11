"""
API routes for Mini-N8N workflow operations.
Fully aligned with WorkflowRunner, Registry, Storage, and FastAPI architecture.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from core.workflow import Workflow, WorkflowNode, WorkflowConnection, WorkflowRunner
from core.registry import registry
from storage.database import get_database
from storage.models import ExecutionStatus
from storage.serialization import WorkflowSerializer

router = APIRouter()


# ============================================================
# Request/Response Models
# ============================================================

class CreateWorkflowRequest(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    connections: List[Dict[str, Any]] = Field(default_factory=list)


class UpdateWorkflowRequest(BaseModel):
    name: Optional[str]
    description: Optional[str]
    nodes: Optional[List[Dict[str, Any]]]
    connections: Optional[List[Dict[str, Any]]]


class ExecuteWorkflowRequest(BaseModel):
    input_data: Dict[str, Any] = Field(default_factory=dict)
    use_cache: bool = True


class PreviewNodeRequest(BaseModel):
    type: str
    config: Dict[str, Any]
    inputs: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# WORKFLOW ROUTES
# ============================================================

@router.post("/workflows/", status_code=201)
async def create_workflow(request: CreateWorkflowRequest):
    """Create a new workflow."""
    try:
        workflow = Workflow(name=request.name, description=request.description)

        for node_data in request.nodes:
            workflow.add_node(WorkflowNode(**node_data))

        for conn_data in request.connections:
            workflow.add_connection(WorkflowConnection(**conn_data))

        errors = workflow.validate_structure()
        if errors:
            raise HTTPException(status_code=400, detail=errors)

        db = get_database()
        saved = await db.create_workflow(workflow.to_dict())

        return saved.data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    db = get_database()
    model = await db.get_workflow(workflow_id)

    if not model:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return model.data


@router.get("/workflows/")
async def list_workflows(limit: int = 100, offset: int = 0):
    db = get_database()
    items = await db.list_workflows(limit=limit, offset=offset)

    return {
        "workflows": [i.data for i in items],
        "total": len(items)
    }


@router.put("/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, request: UpdateWorkflowRequest):
    db = get_database()
    existing = await db.get_workflow(workflow_id)

    if not existing:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = Workflow.from_dict(existing.data)

    if request.name is not None:
        workflow.name = request.name

    if request.description is not None:
        workflow.description = request.description

    if request.nodes:
        workflow.nodes = [WorkflowNode(**n) for n in request.nodes]

    if request.connections:
        workflow.connections = [WorkflowConnection(**c) for c in request.connections]

    workflow.version += 1

    errors = workflow.validate_structure()
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    updated = await db.update_workflow(workflow_id, workflow.to_dict())

    return updated.data


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    db = get_database()
    success = await db.delete_workflow(workflow_id)

    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {"message": "Workflow deleted successfully"}


# ============================================================
# EXECUTION ROUTES
# ============================================================

@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    background: BackgroundTasks
):
    """
    Starts workflow execution in background.
    """
    db = get_database()
    model = await db.get_workflow(workflow_id)

    if not model:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = Workflow.from_dict(model.data)

    execution_id = str(uuid.uuid4())

    await db.create_execution(
        execution_id=execution_id,
        workflow_id=workflow_id,
        input_data=request.input_data
    )

    background.add_task(
        _background_execute,
        workflow,
        execution_id,
        request.input_data,
        request.use_cache
    )

    return {
        "execution_id": execution_id,
        "status": "pending",
        "workflow_id": workflow_id
    }


async def _background_execute(workflow, execution_id, input_data, use_cache):
    db = get_database()

    await db.update_execution(
        execution_id,
        status=ExecutionStatus.RUNNING,
        started_at=datetime.utcnow()
    )

    runner = WorkflowRunner(workflow)

    try:
        result = await runner.run(input_data=input_data)

        await db.update_execution(
            execution_id,
            status=ExecutionStatus.SUCCESS,
            output_data=result.output,
            error=result.error,
            node_results=result.node_results,
            execution_order=result.execution_order,
            finished_at=result.finished_at,
            execution_time=result.execution_time
        )

    except Exception as e:
        await db.update_execution(
            execution_id,
            status=ExecutionStatus.FAILED,
            error=str(e),
            finished_at=datetime.utcnow()
        )


@router.get("/workflows/{workflow_id}/executions/{execution_id}")
async def get_execution(workflow_id: str, execution_id: str):
    db = get_database()
    execution = await db.get_execution(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution.to_dict()


@router.get("/workflows/{workflow_id}/executions/")
async def list_executions(workflow_id: str, limit: int = 100, offset: int = 0):
    db = get_database()
    items = await db.list_executions(workflow_id, limit, offset)

    return {
        "executions": [i.to_dict() for i in items],
        "total": len(items)
    }


# ============================================================
# NODE TYPE ROUTES
# ============================================================

@router.get("/node-types/")
async def list_node_types():
    types = registry.list_all()
    return {
        "node_types": [
            {
                "type": t.type_name,
                "display_name": t.display_name,
                "description": t.description,
                "category": t.category,
                "config_schema": t.config_schema,
                "input_schema": t.input_schema,
                "output_schema": t.output_schema,
                "icon": t.icon
            }
            for t in types
        ],
        "categories": registry.get_categories()
    }


@router.get("/node-types/{type_name}")
async def get_node_type(type_name: str):
    info = registry.get(type_name)
    if not info:
        raise HTTPException(status_code=404, detail="Node type not found")

    return info.__dict__


@router.post("/nodes/{type_name}/preview")
async def preview_node(type_name: str, request: PreviewNodeRequest):
    cls = registry.get_class(type_name)
    if not cls:
        raise HTTPException(status_code=404, detail="Node type not found")

    node = cls(node_id="preview", config=request.config)

    # Validate config
    errors = node.validate_config()
    if errors:
        raise HTTPException(status_code=400, detail=errors)

    try:
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
