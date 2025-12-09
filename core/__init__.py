"""
Core package initialization.

This module exposes the main workflow engine components and ensures that
all built-in nodes are registered when the package is imported.

Exports:
- Workflow, WorkflowNode, WorkflowConnection
- WorkflowRunner
- registry (global node registry)
- DAG, TopologicalSorter

Note:
Node registration is performed automatically so any runtime environment
that imports `core` immediately gains access to all built-in node types.
"""

from .workflow import Workflow, WorkflowNode, WorkflowConnection, WorkflowRunner
from .registry import registry
from .dag import DAG, TopologicalSorter

# Auto-register all built-in nodes
try:
    from nodes.registry_setup import register_all_nodes
    register_all_nodes()
except Exception as e:
    # Silently fail but log if needed
    print(f"[core.__init__] Warning: Failed to auto-register nodes: {e}")

__all__ = [
    "Workflow",
    "WorkflowNode",
    "WorkflowConnection",
    "WorkflowRunner",
    "registry",
    "DAG",
    "TopologicalSorter",
]
