"""Database models for workflows and executions."""

from sqlalchemy import Column, String, Text, Integer, DateTime, Enum, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class ExecutionStatus(str, enum.Enum):
    """Execution status enum."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowModel(Base):
    """Database model for workflows."""
    
    __tablename__ = "workflows"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    data = Column(JSON, nullable=False)  # Full workflow JSON
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Workflow(id={self.id}, name={self.name})>"


class ExecutionModel(Base):
    """Database model for workflow executions."""
    
    __tablename__ = "executions"
    
    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(36), nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    node_results = Column(JSON, nullable=True)  # Results from each node
    execution_order = Column(JSON, nullable=True)  # Order nodes were executed
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    execution_time = Column(Float, nullable=True)  # Seconds
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Execution(id={self.id}, workflow_id={self.workflow_id}, status={self.status})>"


