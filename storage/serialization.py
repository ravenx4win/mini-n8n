"""
Workflow serialization layer for Mini-N8N.
Provides safe conversion between Workflow <-> JSON <-> dict,
including support for datetime, enums, and Pydantic v2 models.
"""

from typing import Dict, Any
from pathlib import Path
import json
import hashlib

from core.workflow import Workflow


# -------------------------------------------------------------
# Custom JSON Encoder (datetime, enums, UUID, pydantic objects)
# -------------------------------------------------------------
class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Pydantic models → dict
        if hasattr(obj, "model_dump"):
            return obj.model_dump()

        # Enum → value
        if hasattr(obj, "value"):
            return obj.value

        # datetime → isoformat
        try:
            return obj.isoformat()
        except Exception:
            pass

        # Fallback
        return str(obj)


# -------------------------------------------------------------
# Workflow Serializer
# -------------------------------------------------------------
class WorkflowSerializer:
    """Serialize and deserialize workflows in a safe and structured format."""

    # -----------------------------------------------------
    # Serialization → JSON String
    # -----------------------------------------------------
    @staticmethod
    def to_json(workflow: Workflow, pretty: bool = True) -> str:
        data = workflow.model_dump()

        if pretty:
            return json.dumps(data, indent=2, cls=EnhancedJSONEncoder)

        return json.dumps(data, cls=EnhancedJSONEncoder)

    # -----------------------------------------------------
    # Parsing JSON → Workflow object
    # -----------------------------------------------------
    @staticmethod
    def from_json(json_str: str) -> Workflow:
        data = json.loads(json_str)
        return Workflow.model_validate(data)

    # -----------------------------------------------------
    # Save Workflow to file
    # -----------------------------------------------------
    @staticmethod
    def to_file(workflow: Workflow, filepath: str, pretty: bool = True) -> None:
        json_str = WorkflowSerializer.to_json(workflow, pretty=pretty)
        Path(filepath).write_text(json_str, encoding="utf-8")

    # -----------------------------------------------------
    # Load Workflow from file
    # -----------------------------------------------------
    @staticmethod
    def from_file(filepath: str) -> Workflow:
        json_str = Path(filepath).read_text(encoding="utf-8")
        return WorkflowSerializer.from_json(json_str)

    # -----------------------------------------------------
    # Convert Workflow → dict
    # -----------------------------------------------------
    @staticmethod
    def to_dict(workflow: Workflow) -> Dict[str, Any]:
        return workflow.model_dump()

    # -----------------------------------------------------
    # Convert dict → Workflow
    # -----------------------------------------------------
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Workflow:
        return Workflow.model_validate(data)

    # -----------------------------------------------------
    # Workflow checksum (useful for versioning)
    # -----------------------------------------------------
    @staticmethod
    def compute_checksum(workflow: Workflow) -> str:
        """Compute SHA256 checksum of workflow content."""
        content = WorkflowSerializer.to_json(workflow, pretty=False)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
