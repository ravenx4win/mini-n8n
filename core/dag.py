"""DAG (Directed Acyclic Graph) implementation for workflow orchestration."""

from typing import Dict, List, Set, Optional
from collections import defaultdict, deque


class CycleDetectedError(Exception):
    """Raised when a cycle is detected in the DAG."""
    pass


class DAG:
    """Directed Acyclic Graph for managing workflow dependencies."""
    
    def __init__(self):
        """Initialize an empty DAG."""
        self.nodes: Set[str] = set()
        self.edges: Dict[str, List[str]] = defaultdict(list)
        self.reverse_edges: Dict[str, List[str]] = defaultdict(list)
    
    def add_node(self, node_id: str) -> None:
        """Add a node to the DAG.
        
        Args:
            node_id: Unique identifier for the node
        """
        self.nodes.add(node_id)
    
    def add_edge(self, from_node: str, to_node: str) -> None:
        """Add a directed edge from one node to another.
        
        Args:
            from_node: Source node ID
            to_node: Destination node ID
            
        Raises:
            CycleDetectedError: If adding this edge would create a cycle
        """
        if from_node not in self.nodes:
            self.add_node(from_node)
        if to_node not in self.nodes:
            self.add_node(to_node)
        
        # Add edge
        self.edges[from_node].append(to_node)
        self.reverse_edges[to_node].append(from_node)
        
        # Check for cycles
        if self._has_cycle():
            # Rollback
            self.edges[from_node].remove(to_node)
            self.reverse_edges[to_node].remove(from_node)
            raise CycleDetectedError(
                f"Adding edge from {from_node} to {to_node} would create a cycle"
            )
    
    def _has_cycle(self) -> bool:
        """Check if the DAG contains a cycle using DFS.
        
        Returns:
            True if a cycle is detected, False otherwise
        """
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self.edges.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False
    
    def get_dependencies(self, node_id: str) -> List[str]:
        """Get all nodes that the given node depends on (incoming edges).
        
        Args:
            node_id: Node to get dependencies for
            
        Returns:
            List of node IDs that are dependencies
        """
        return self.reverse_edges.get(node_id, [])
    
    def get_dependents(self, node_id: str) -> List[str]:
        """Get all nodes that depend on the given node (outgoing edges).
        
        Args:
            node_id: Node to get dependents for
            
        Returns:
            List of node IDs that depend on this node
        """
        return self.edges.get(node_id, [])


class TopologicalSorter:
    """Performs topological sorting on a DAG to determine execution order."""
    
    @staticmethod
    def sort(dag: DAG) -> List[str]:
        """Sort nodes in topological order using Kahn's algorithm.
        
        Args:
            dag: The DAG to sort
            
        Returns:
            List of node IDs in topological order
            
        Raises:
            CycleDetectedError: If the graph contains a cycle
        """
        # Calculate in-degree for each node
        in_degree = {node: 0 for node in dag.nodes}
        for node in dag.nodes:
            for dependent in dag.get_dependents(node):
                in_degree[dependent] += 1
        
        # Queue of nodes with no dependencies
        queue = deque([node for node in dag.nodes if in_degree[node] == 0])
        result = []
        
        while queue:
            # Process node with no dependencies
            node = queue.popleft()
            result.append(node)
            
            # Reduce in-degree for dependent nodes
            for dependent in dag.get_dependents(node):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # If all nodes are processed, return the sorted list
        if len(result) == len(dag.nodes):
            return result
        else:
            # Cycle detected
            raise CycleDetectedError("Cannot sort DAG: cycle detected")
    
    @staticmethod
    def get_execution_levels(dag: DAG) -> List[List[str]]:
        """Group nodes into execution levels for parallel processing.
        
        Nodes in the same level have no dependencies on each other and can
        be executed in parallel.
        
        Args:
            dag: The DAG to analyze
            
        Returns:
            List of levels, where each level is a list of node IDs
        """
        in_degree = {node: len(dag.get_dependencies(node)) for node in dag.nodes}
        levels = []
        
        while any(degree == 0 for degree in in_degree.values()):
            # Current level: nodes with no remaining dependencies
            current_level = [
                node for node, degree in in_degree.items() if degree == 0
            ]
            
            if not current_level:
                break
            
            levels.append(current_level)
            
            # Remove processed nodes and update dependencies
            for node in current_level:
                in_degree[node] = -1  # Mark as processed
                for dependent in dag.get_dependents(node):
                    if in_degree[dependent] > 0:
                        in_degree[dependent] -= 1
        
        return levels


