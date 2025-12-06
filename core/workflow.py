"""Workflow data structures and management."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


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
    position: Optional[Dict[str, float]] = Field(
        default=None, description="Visual position (x, y) for frontend"
    )
    name: Optional[str] = Field(default=None, description="Human-readable node name")
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.name is None:
            self.name = f"{self.type}_{self.id[:8]}"


class Workflow(BaseModel):
    """Represents a complete workflow with nodes and connections."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique workflow ID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    nodes: List[WorkflowNode] = Field(default_factory=list, description="List of nodes")
    connections: List[WorkflowConnection] = Field(
        default_factory=list, description="List of connections"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1, description="Workflow version")
    
    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get a node by ID.
        
        Args:
            node_id: Node ID to find
            
        Returns:
            WorkflowNode if found, None otherwise
        """
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def add_node(self, node: WorkflowNode) -> None:
        """Add a node to the workflow.
        
        Args:
            node: Node to add
        """
        self.nodes.append(node)
        self.updated_at = datetime.utcnow()
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its connections from the workflow.
        
        Args:
            node_id: ID of node to remove
            
        Returns:
            True if node was removed, False if not found
        """
        node = self.get_node(node_id)
        if node is None:
            return False
        
        # Remove node
        self.nodes = [n for n in self.nodes if n.id != node_id]
        
        # Remove associated connections
        self.connections = [
            c for c in self.connections
            if c.from_node != node_id and c.to_node != node_id
        ]
        
        self.updated_at = datetime.utcnow()
        return True
    
    def add_connection(self, connection: WorkflowConnection) -> None:
        """Add a connection between nodes.
        
        Args:
            connection: Connection to add
        """
        self.connections.append(connection)
        self.updated_at = datetime.utcnow()
    
    def get_node_inputs(self, node_id: str) -> List[WorkflowConnection]:
        """Get all incoming connections for a node.
        
        Args:
            node_id: Node ID
            
        Returns:
            List of connections where this node is the destination
        """
        return [c for c in self.connections if c.to_node == node_id]
    
    def get_node_outputs(self, node_id: str) -> List[WorkflowConnection]:
        """Get all outgoing connections for a node.
        
        Args:
            node_id: Node ID
            
        Returns:
            List of connections where this node is the source
        """
        return [c for c in self.connections if c.from_node == node_id]
    
    def validate_structure(self) -> List[str]:
        """Validate workflow structure and return any errors.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check that all connection nodes exist
        node_ids = {node.id for node in self.nodes}
        for conn in self.connections:
            if conn.from_node not in node_ids:
                errors.append(f"Connection references non-existent node: {conn.from_node}")
            if conn.to_node not in node_ids:
                errors.append(f"Connection references non-existent node: {conn.to_node}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary for serialization.
        
        Returns:
            Dictionary representation of workflow
        """
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        """Create workflow from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Workflow instance
        """
        return cls(**data)


