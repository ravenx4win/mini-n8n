"""Dynamic node registry for managing available node types."""

from typing import Dict, Type, List, Optional, Any
from dataclasses import dataclass


@dataclass
class NodeTypeInfo:
    """Information about a registered node type."""
    
    type_name: str
    display_name: str
    description: str
    category: str
    node_class: Type
    config_schema: Dict[str, Any]
    icon: Optional[str] = None


class NodeRegistry:
    """Registry for managing available node types."""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure one registry instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the registry."""
        if self._initialized:
            return
        
        self._nodes: Dict[str, NodeTypeInfo] = {}
        self._initialized = True
    
    def register(
        self,
        type_name: str,
        node_class: Type,
        display_name: str,
        description: str,
        category: str,
        config_schema: Dict[str, Any],
        icon: Optional[str] = None,
    ) -> None:
        """Register a new node type.
        
        Args:
            type_name: Unique identifier for the node type
            node_class: The node class to instantiate
            display_name: Human-readable name
            description: Description of what the node does
            category: Category (e.g., 'AI', 'Logic', 'I/O')
            config_schema: JSON schema for configuration
            icon: Optional icon identifier
        """
        if type_name in self._nodes:
            raise ValueError(f"Node type '{type_name}' is already registered")
        
        info = NodeTypeInfo(
            type_name=type_name,
            display_name=display_name,
            description=description,
            category=category,
            node_class=node_class,
            config_schema=config_schema,
            icon=icon,
        )
        
        self._nodes[type_name] = info
    
    def get(self, type_name: str) -> Optional[NodeTypeInfo]:
        """Get information about a node type.
        
        Args:
            type_name: Node type identifier
            
        Returns:
            NodeTypeInfo if found, None otherwise
        """
        return self._nodes.get(type_name)
    
    def get_class(self, type_name: str) -> Optional[Type]:
        """Get the node class for a given type.
        
        Args:
            type_name: Node type identifier
            
        Returns:
            Node class if found, None otherwise
        """
        info = self.get(type_name)
        return info.node_class if info else None
    
    def list_all(self) -> List[NodeTypeInfo]:
        """List all registered node types.
        
        Returns:
            List of all node type information
        """
        return list(self._nodes.values())
    
    def list_by_category(self, category: str) -> List[NodeTypeInfo]:
        """List all node types in a specific category.
        
        Args:
            category: Category name
            
        Returns:
            List of node types in the category
        """
        return [info for info in self._nodes.values() if info.category == category]
    
    def get_categories(self) -> List[str]:
        """Get all available categories.
        
        Returns:
            List of unique category names
        """
        return sorted(set(info.category for info in self._nodes.values()))
    
    def create_instance(self, type_name: str, node_id: str, config: Dict[str, Any]):
        """Create an instance of a node.
        
        Args:
            type_name: Node type identifier
            node_id: Unique ID for this node instance
            config: Configuration dictionary
            
        Returns:
            Instance of the node class
            
        Raises:
            ValueError: If node type is not registered
        """
        node_class = self.get_class(type_name)
        if node_class is None:
            raise ValueError(f"Unknown node type: {type_name}")
        
        return node_class(node_id=node_id, config=config)


# Global registry instance
registry = NodeRegistry()


