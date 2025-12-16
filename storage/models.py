"""
Database models for workflows and executions.
Aligned with Mini-N8N executor, routes, and workflow engine.
"""

from sqlalchemy import (
    Column, String, Text, Integer, DateTime, Enum, JSON, Float, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
import enum


# ---------------------------------------------------------
# Base Declarative Class (SQLAlchemy 2.0 compliant)
# ---------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------
# Execution Status Enum
# ---------------------------------------------------------
class ExecutionStatus(str, enum.Enum):
    """Execution status states."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------
# Workflow Model
# ---------------------------------------------------------
class WorkflowModel(Base):
    """
    Stores full workflow JSON configuration:
    - nodes
    - connections
    - metadata
    - name, description, version
    """
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Stores full workflow definition as JSON
    data = Column(JSON, nullable=False)

    version = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Workflow(id={self.id}, name={self.name})>"


# ---------------------------------------------------------
# Execution Model
# ---------------------------------------------------------
class ExecutionModel(Base):
    """
    Stores workflow execution records:
    - Status lifecycle (pending → running → complete)
    - Input / Output
    - Node results
    - Execution order (DAG)
    - Timing info
    """
    __tablename__ = "executions"

    id = Column(String(36), primary_key=True)

    workflow_id = Column(
        String(36),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False
    )

    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)

    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)

    # Per-node results (NodeResult converted to JSON-safe dict)
    node_results = Column(JSON, nullable=True)

    # Ordered list of node IDs
    execution_order = Column(JSON, nullable=True)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    execution_time = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    def __repr__(self):
        return (
            f"<Execution(id={self.id}, workflow_id={self.workflow_id}, "
            f"status={self.status})>"
        )
