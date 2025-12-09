"""
Node Registry
-------------
Central registry for all available workflow node types.

This registry is responsible for:
- Registering node types
- Storing node metadata (schema, category, description, icon)
- Retrieving node classes for workflow execution
- Providing UI-friendly listings for workflow builders

This is the heart of your node-based automation framework.
"""

from typing import Dict, Type, List, Optional, Any
from dataclasses import dataclass, field


# ======================================================================
#  Node Metadata Dataclass
# ======================================================================

@dataclass
class NodeTypeInfo:
    """
    Metadata describing a registered node type.

    This is used by:
    - The workflow executor
    - The frontend workflow builder UI
    - Validation systems
    """
    type_name: str
    display_name: str
    description: str
    category: str
    node_class: Type

    config_schema: Dict[str, Any]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    icon: Optional[str] = None

    # Useful for future UI extensions
    version: str = "1.0"
    enabled: bool = True


# ======================================================================
#  Node Registry (Singleton)
# ======================================================================

class NodeRegistry:
    """
    Registry for managing available node types.

    This is a singleton because all node types must be available globally
    to:
    - The executor
    - The API layer
    - The UI builder
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern for a single global registry."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize only once."""
        if self._initialized:
            return

        self._nodes: Dict[str, NodeTypeInfo] = {}
        self._initialized = True

    # ==================================================================
    #  Registration Logic
    # ==================================================================

    def register(
        self,
        type_name: str,
        node_class: Type,
        display_name: str,
        description: str,
        category: str,
        config_schema: Dict[str, Any],
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        icon: Optional[str] = None,
    ) -> None:
        """
        Register a new node type.

        Parameters:
            type_name      - Unique identifier (e.g. "llm_text_generation")
            node_class     - Python class implementing the node
            display_name   - Human-friendly name ("LLM Text Generation")
            description    - Description of node functionality
            category       - Node category ("AI", "Logic", "Integration", ...)
            config_schema  - JSON schema describing configuration options
            input_schema   - JSON schema describing incoming data
            output_schema  - JSON schema describing output structure
            icon           - Optional icon name for the UI
        """

        if type_name in self._nodes:
            raise ValueError(f"Node type '{type_name}' is already registered.")

        info = NodeTypeInfo(
            type_name=type_name,
            display_name=display_name,
            description=description,
            category=category,
            node_class=node_class,
            config_schema=config_schema,
            input_schema=input_schema,
            output_schema=output_schema,
            icon=icon,
        )

        self._nodes[type_name] = info

    # ==================================================================
    #  Lookup Helpers
    # ==================================================================

    def get(self, type_name: str) -> Optional[NodeTypeInfo]:
        """Return metadata for the node type."""
        return self._nodes.get(type_name)

    def get_class(self, type_name: str) -> Optional[Type]:
        """Return the class implementing the given node type."""
        info = self.get(type_name)
        return info.node_class if info else None

    def create_instance(self, type_name: str, node_id: str, config: Dict[str, Any]):
        """
        Create an instance of a node given its type name and configuration.
        """
        cls = self.get_class(type_name)
        if cls is None:
            raise ValueError(f"Unknown node type: '{type_name}'")

        return cls(node_id=node_id, config=config)

    # ==================================================================
    #  Listing + UI Helpers
    # ==================================================================

    def list_all(self) -> List[NodeTypeInfo]:
        """Return metadata for all registered nodes."""
        return list(self._nodes.values())

    def list_by_category(self, category: str) -> List[NodeTypeInfo]:
        """Return nodes belonging to a specific category."""
        return [info for info in self._nodes.values() if info.category == category]

    def get_categories(self) -> List[str]:
        """Return all categories used by registered node types."""
        return sorted(set(info.category for info in self._nodes.values()))


# ======================================================================
#  Global Registry Instance
# ======================================================================

registry = NodeRegistry()
