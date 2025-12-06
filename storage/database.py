"""Database connection and management."""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, delete
from contextlib import asynccontextmanager
import os

from .models import Base, WorkflowModel, ExecutionModel, ExecutionStatus


class Database:
    """Database manager for workflows and executions."""
    
    def __init__(self, database_url: str):
        """Initialize database connection.
        
        Args:
            database_url: Database connection URL
        """
        # Convert sqlite URL to async version
        if database_url.startswith("sqlite:///"):
            database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def init_db(self):
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self):
        """Close database connection."""
        await self.engine.dispose()
    
    @asynccontextmanager
    async def session(self):
        """Get a database session."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    # Workflow operations
    
    async def create_workflow(self, workflow_data: Dict[str, Any]) -> WorkflowModel:
        """Create a new workflow.
        
        Args:
            workflow_data: Workflow data dictionary
            
        Returns:
            Created workflow model
        """
        async with self.session() as session:
            workflow = WorkflowModel(
                id=workflow_data["id"],
                name=workflow_data["name"],
                description=workflow_data.get("description"),
                data=workflow_data,
                version=workflow_data.get("version", 1)
            )
            session.add(workflow)
            await session.flush()
            await session.refresh(workflow)
            return workflow
    
    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowModel]:
        """Get a workflow by ID.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Workflow model or None
        """
        async with self.session() as session:
            result = await session.execute(
                select(WorkflowModel).where(WorkflowModel.id == workflow_id)
            )
            return result.scalar_one_or_none()
    
    async def list_workflows(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[WorkflowModel]:
        """List all workflows.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of workflow models
        """
        async with self.session() as session:
            result = await session.execute(
                select(WorkflowModel)
                .order_by(WorkflowModel.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
    
    async def update_workflow(
        self,
        workflow_id: str,
        workflow_data: Dict[str, Any]
    ) -> Optional[WorkflowModel]:
        """Update a workflow.
        
        Args:
            workflow_id: Workflow ID
            workflow_data: Updated workflow data
            
        Returns:
            Updated workflow model or None
        """
        async with self.session() as session:
            result = await session.execute(
                select(WorkflowModel).where(WorkflowModel.id == workflow_id)
            )
            workflow = result.scalar_one_or_none()
            
            if workflow:
                workflow.name = workflow_data.get("name", workflow.name)
                workflow.description = workflow_data.get("description", workflow.description)
                workflow.data = workflow_data
                workflow.version = workflow_data.get("version", workflow.version)
                await session.flush()
                await session.refresh(workflow)
            
            return workflow
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            True if deleted, False if not found
        """
        async with self.session() as session:
            result = await session.execute(
                delete(WorkflowModel).where(WorkflowModel.id == workflow_id)
            )
            return result.rowcount > 0
    
    # Execution operations
    
    async def create_execution(
        self,
        execution_id: str,
        workflow_id: str,
        input_data: Optional[Dict[str, Any]] = None
    ) -> ExecutionModel:
        """Create a new execution.
        
        Args:
            execution_id: Execution ID
            workflow_id: Workflow ID
            input_data: Input data for execution
            
        Returns:
            Created execution model
        """
        async with self.session() as session:
            execution = ExecutionModel(
                id=execution_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.PENDING,
                input_data=input_data
            )
            session.add(execution)
            await session.flush()
            await session.refresh(execution)
            return execution
    
    async def get_execution(self, execution_id: str) -> Optional[ExecutionModel]:
        """Get an execution by ID.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Execution model or None
        """
        async with self.session() as session:
            result = await session.execute(
                select(ExecutionModel).where(ExecutionModel.id == execution_id)
            )
            return result.scalar_one_or_none()
    
    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ExecutionModel]:
        """List executions.
        
        Args:
            workflow_id: Optional workflow ID to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of execution models
        """
        async with self.session() as session:
            query = select(ExecutionModel)
            
            if workflow_id:
                query = query.where(ExecutionModel.workflow_id == workflow_id)
            
            query = query.order_by(ExecutionModel.created_at.desc()).limit(limit).offset(offset)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def update_execution(
        self,
        execution_id: str,
        status: Optional[ExecutionStatus] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        node_results: Optional[Dict[str, Any]] = None,
        execution_order: Optional[List[str]] = None,
        started_at: Optional[Any] = None,
        finished_at: Optional[Any] = None,
        execution_time: Optional[float] = None
    ) -> Optional[ExecutionModel]:
        """Update an execution.
        
        Args:
            execution_id: Execution ID
            status: New status
            output_data: Output data
            error: Error message
            node_results: Results from each node
            execution_order: Order nodes were executed
            started_at: Start timestamp
            finished_at: Finish timestamp
            execution_time: Execution time in seconds
            
        Returns:
            Updated execution model or None
        """
        async with self.session() as session:
            result = await session.execute(
                select(ExecutionModel).where(ExecutionModel.id == execution_id)
            )
            execution = result.scalar_one_or_none()
            
            if execution:
                if status is not None:
                    execution.status = status
                if output_data is not None:
                    execution.output_data = output_data
                if error is not None:
                    execution.error = error
                if node_results is not None:
                    execution.node_results = node_results
                if execution_order is not None:
                    execution.execution_order = execution_order
                if started_at is not None:
                    execution.started_at = started_at
                if finished_at is not None:
                    execution.finished_at = finished_at
                if execution_time is not None:
                    execution.execution_time = execution_time
                
                await session.flush()
                await session.refresh(execution)
            
            return execution


# Global database instance
_database: Optional[Database] = None


def get_database() -> Database:
    """Get the global database instance.
    
    Returns:
        Database instance
    """
    global _database
    if _database is None:
        database_url = os.getenv("DATABASE_URL", "sqlite:///./workflows.db")
        _database = Database(database_url)
    return _database


async def init_database():
    """Initialize the global database."""
    db = get_database()
    await db.init_db()


