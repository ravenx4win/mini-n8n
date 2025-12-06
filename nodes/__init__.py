"""
Nodes Package
-------------
Provides all built-in workflow node implementations (Input, AI, Logic, HTTP, Output)
and registers them with the global workflow registry.

This ensures that whenever `nodes` is imported, all node types become available
for workflow creation and execution.
"""

from .base import BaseNode, NodeResult, NodeExecutionError
from .registry_setup import register_all_nodes

# Import node classes for explicit export
from .input_node import UserInputNode
from .llm_node import LLMTextGenerationNode
from .image_node import ImageGenerationNode
from .video_node import VideoGenerationNode
from .http_node import HTTPRequestNode
from .conditional_node import ConditionalLogicNode
from .output_node import OutputNode

__all__ = [
    # Base Components
    "BaseNode",
    "NodeResult",
    "NodeExecutionError",

    # Node Implementations
    "UserInputNode",
    "LLMTextGenerationNode",
    "ImageGenerationNode",
    "VideoGenerationNode",
    "HTTPRequestNode",
    "ConditionalLogicNode",
    "OutputNode",

    # Registration
    "register_all_nodes",
]

# Automatically register all built-in nodes when package loads
try:
    register_all_nodes()
except Exception as e:
    # Safe fallback: avoid crashing import
    print(f"[nodes] Warning: Node registration failed: {e}")
