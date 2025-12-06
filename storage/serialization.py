"""Workflow serialization to/from JSON."""

from typing import Dict, Any
import json
from pathlib import Path

from core.workflow import Workflow


class WorkflowSerializer:
    """Serialize and deserialize workflows to/from JSON."""
    
    @staticmethod
    def to_json(workflow: Workflow) -> str:
        """Serialize workflow to JSON string.
        
        Args:
            workflow: Workflow to serialize
            
        Returns:
            JSON string
        """
        data = workflow.to_dict()
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def from_json(json_str: str) -> Workflow:
        """Deserialize workflow from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            Workflow object
        """
        data = json.loads(json_str)
        return Workflow.from_dict(data)
    
    @staticmethod
    def to_file(workflow: Workflow, filepath: str) -> None:
        """Save workflow to JSON file.
        
        Args:
            workflow: Workflow to save
            filepath: Path to file
        """
        json_str = WorkflowSerializer.to_json(workflow)
        Path(filepath).write_text(json_str)
    
    @staticmethod
    def from_file(filepath: str) -> Workflow:
        """Load workflow from JSON file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Workflow object
        """
        json_str = Path(filepath).read_text()
        return WorkflowSerializer.from_json(json_str)
    
    @staticmethod
    def to_dict(workflow: Workflow) -> Dict[str, Any]:
        """Convert workflow to dictionary.
        
        Args:
            workflow: Workflow to convert
            
        Returns:
            Dictionary representation
        """
        return workflow.to_dict()
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Workflow:
        """Create workflow from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Workflow object
        """
        return Workflow.from_dict(data)


