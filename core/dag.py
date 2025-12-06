"""
DAG (Directed Acyclic Graph) implementation for workflow orchestration.

This module provides:
- A DAG class for node + edge management
- Cycle detection
- Topological sorting (Kahn's Algorithm)
- Parallel execution level grouping
- DAG validation helpers
"""

from typing import Dict, List, Set
from collections import defaultdict, deque


class CycleDetectedError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


class DAGValidationError(Exception):
    """Raised when the DAG structure is invalid."""
    pass


class DAG:
    """Directed Acyclic Graph for managing workflow dependencies."""

    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)

    # -----------------------------
    # Node + Edge Management
    # -----------------------------

    def add_node(self, node_id: str) -> None:
        """Add a node to the DAG."""
        if not isinstance(node_id, str) or not node_id.strip():
            raise DAGValidationError(f"Invalid node_id '{node_id}'")
        self.nodes.add(node_id)

    def add_edge(self, from_node: str, to_node: str) -> None:
        """
        Add a directed edge from one node to another.

        Raises:
            CycleDetectedError: If adding this edge creates a cycle.
            DAGValidationError: If referencing missing node IDs.
        """
        if from_node not in self.nodes:
            raise DAGValidationError(f"Node '{from_node}' not found in DAG.")
        if to_node not in self.nodes:
            raise DAGValidationError(f"Node '{to_node}' not found in DAG.")
        if from_node == to_node:
            raise CycleDetectedError("Self-cycle detected")

        # Add edge temporarily
        self.edges[from_node].append(to_node)
        self.reverse_edges[to_node].append(from_node)

        # Check for cycle
        if self._detect_cycle():
            # Rollback
            self.edges[from_node].remove(to_node)
            self.reverse_edges[to_node].remove(from_node)
            raise CycleDetectedError(
                f"Adding edge {from_node} -> {to_node} creates a cycle."
            )

    # -----------------------------
    # Cycle Detection
    # -----------------------------

    def _detect_cycle(self) -> bool:
        """Detect cycles using Kahn's algorithm (in-degree counter)."""
        in_degree = {node: len(self.reverse_edges[node]) for node in self.nodes}
        q = deque([n for n, deg in in_degree.items() if deg == 0])
        visited = 0

        while q:
            node = q.popleft()
            visited += 1
            for dep in self.edges[node]:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    q.append(dep)

        return visited != len(self.nodes)

    # -----------------------------
    # Query Helpers
    # -----------------------------

    def get_dependencies(self, node_id: str) -> List[str]:
        """Return incoming nodes for a given node."""
        return self.reverse_edges.get(node_id, [])

    def get_dependents(self, node_id: str) -> List[str]:
        """Return outgoing nodes for a given node."""
        return self.edges.get(node_id, [])

    # -----------------------------
    # Validation Helpers
    # -----------------------------

    def validate_all_nodes_present(self, workflow_nodes: Set[str]) -> None:
        """Ensure workflow references match DAG nodes."""
        missing = workflow_nodes - self.nodes
        if missing:
            raise DAGValidationError(f"Missing nodes in DAG: {missing}")

    def validate(self) -> None:
        """Ensure the DAG is valid and acyclic."""
        if self._detect_cycle():
            raise CycleDetectedError("DAG contains a cycle.")
        if len(self.nodes) == 0:
            raise DAGValidationError("DAG contains no nodes.")

    # -----------------------------
    # Debugging / Inspection
    # -----------------------------

    def describe(self) -> Dict[str, List[str]]:
        """Return a representation of the DAG."""
        return {node: self.edges[node] for node in self.nodes}


# ============================================================
# Topological Sorting + Execution Level Grouping
# ============================================================

class TopologicalSorter:
    """Perform topological sorting and execution level grouping."""

    @staticmethod
    def topological_sort(dag: DAG) -> List[str]:
        """Return node IDs in a valid execution order."""
        dag.validate()
        in_degree = {node: len(dag.get_dependencies(node)) for node in dag.nodes}
        q = deque([node for node, deg in in_degree.items() if deg == 0])

        result = []

        while q:
            node = q.popleft()
            result.append(node)

            for dep in dag.get_dependents(node):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    q.append(dep)

        if len(result) != len(dag.nodes):
            raise CycleDetectedError("Cycle detected during topological sort")

        return result

    @staticmethod
    def execution_levels(dag: DAG) -> List[List[str]]:
        """
        Group nodes into parallel-executable layers.

        Example:
            Level 0: ["node1"]
            Level 1: ["node2", "node3"]
            Level 2: ["node4"]
        """
        dag.validate()
        in_degree = {n: len(dag.get_dependencies(n)) for n in dag.nodes}
        levels: List[List[str]] = []

        while True:
            level = [n for n, deg in in_degree.items() if deg == 0]
            if not level:
                break

            levels.append(level)

            for node in level:
                in_degree[node] = -1  # Mark processed
                for dep in dag.get_dependents(node):
                    in_degree[dep] -= 1

        # Safety: ensure no unprocessed nodes
        leftover = [n for n, deg in in_degree.items() if deg >= 0]
        if leftover:
            raise CycleDetectedError(
                f"Unreachable or cyclic nodes detected: {leftover}"
            )

        return levels
