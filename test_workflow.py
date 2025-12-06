"""Test script to verify the workflow automation engine."""

import asyncio
import json
from core.workflow import Workflow, WorkflowNode, WorkflowConnection
from executor.engine import WorkflowExecutor
from nodes.registry_setup import register_all_nodes
from storage.database import init_database


async def test_simple_workflow():
    """Test a simple workflow with user input and output."""
    print("=" * 60)
    print("TEST: Simple Input -> Output Workflow")
    print("=" * 60)
    
    # Create workflow
    workflow = Workflow(
        name="Simple Test",
        description="Test input and output nodes"
    )
    
    # Add input node
    input_node = WorkflowNode(
        id="input1",
        type="user_input",
        config={
            "input_key": "message",
            "default": "Hello, World!"
        }
    )
    workflow.add_node(input_node)
    
    # Add output node
    output_node = WorkflowNode(
        id="output1",
        type="output",
        config={
            "format": "text"
        }
    )
    workflow.add_node(output_node)
    
    # Connect nodes
    workflow.add_connection(
        WorkflowConnection(from_node="input1", to_node="output1")
    )
    
    # Execute
    executor = WorkflowExecutor()
    result = await executor.execute(
        workflow=workflow,
        input_data={"message": "Test message from input"}
    )
    
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print()
    
    return result.success


async def test_conditional_workflow():
    """Test a workflow with conditional logic."""
    print("=" * 60)
    print("TEST: Conditional Logic Workflow")
    print("=" * 60)
    
    workflow = Workflow(
        name="Conditional Test",
        description="Test conditional branching"
    )
    
    # Input node
    input_node = WorkflowNode(
        id="input1",
        type="user_input",
        config={
            "input_key": "number",
            "default": "10"
        }
    )
    workflow.add_node(input_node)
    
    # Conditional node
    conditional_node = WorkflowNode(
        id="cond1",
        type="conditional_logic",
        config={
            "condition_type": "greater_than",
            "value1": "{{input1.output}}",
            "value2": "5"
        }
    )
    workflow.add_node(conditional_node)
    
    # Output node
    output_node = WorkflowNode(
        id="output1",
        type="output",
        config={"format": "json"}
    )
    workflow.add_node(output_node)
    
    # Connect
    workflow.add_connection(WorkflowConnection(from_node="input1", to_node="cond1"))
    workflow.add_connection(WorkflowConnection(from_node="cond1", to_node="output1"))
    
    # Execute
    executor = WorkflowExecutor()
    result = await executor.execute(
        workflow=workflow,
        input_data={"number": "10"}
    )
    
    print(f"Success: {result.success}")
    print(f"Condition result: {result.output}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print()
    
    return result.success


async def test_http_workflow():
    """Test a workflow with HTTP request."""
    print("=" * 60)
    print("TEST: HTTP Request Workflow")
    print("=" * 60)
    
    workflow = Workflow(
        name="HTTP Test",
        description="Test HTTP request node"
    )
    
    # HTTP request node
    http_node = WorkflowNode(
        id="http1",
        type="http_request",
        config={
            "method": "GET",
            "url": "https://jsonplaceholder.typicode.com/todos/1",
            "timeout": 10
        }
    )
    workflow.add_node(http_node)
    
    # Output node
    output_node = WorkflowNode(
        id="output1",
        type="output",
        config={"format": "json"}
    )
    workflow.add_node(output_node)
    
    # Connect
    workflow.add_connection(WorkflowConnection(from_node="http1", to_node="output1"))
    
    # Execute
    executor = WorkflowExecutor()
    result = await executor.execute(workflow=workflow)
    
    print(f"Success: {result.success}")
    print(f"HTTP Response: {json.dumps(result.output, indent=2)}")
    print(f"Execution time: {result.execution_time:.2f}s")
    print()
    
    return result.success


async def test_caching():
    """Test workflow execution caching."""
    print("=" * 60)
    print("TEST: Execution Caching")
    print("=" * 60)
    
    workflow = Workflow(name="Cache Test")
    
    # HTTP node (same as previous test)
    http_node = WorkflowNode(
        id="http1",
        type="http_request",
        config={
            "method": "GET",
            "url": "https://jsonplaceholder.typicode.com/todos/1",
            "timeout": 10
        }
    )
    workflow.add_node(http_node)
    
    output_node = WorkflowNode(
        id="output1",
        type="output",
        config={"format": "json"}
    )
    workflow.add_node(output_node)
    
    workflow.add_connection(WorkflowConnection(from_node="http1", to_node="output1"))
    
    # First execution
    executor = WorkflowExecutor()
    result1 = await executor.execute(workflow=workflow, use_cache=True)
    time1 = result1.execution_time
    
    # Second execution (should use cache)
    result2 = await executor.execute(workflow=workflow, use_cache=True)
    time2 = result2.execution_time
    
    # Get cache stats
    stats = executor.cache.get_stats()
    
    print(f"First execution: {time1:.2f}s")
    print(f"Second execution (cached): {time2:.2f}s")
    print(f"Cache stats: {stats}")
    print(f"Speedup: {time1/time2:.1f}x faster" if time2 > 0 else "N/A")
    print()
    
    return result1.success and result2.success


async def test_from_json():
    """Test loading and executing workflow from JSON file."""
    print("=" * 60)
    print("TEST: Load Workflow from JSON")
    print("=" * 60)
    
    try:
        # Load example workflow
        with open("examples/data_enrichment.json") as f:
            data = json.load(f)
        
        workflow = Workflow.from_dict(data)
        
        print(f"Loaded workflow: {workflow.name}")
        print(f"Nodes: {len(workflow.nodes)}")
        print(f"Connections: {len(workflow.connections)}")
        
        # Execute
        executor = WorkflowExecutor()
        result = await executor.execute(workflow=workflow)
        
        print(f"Success: {result.success}")
        if result.error:
            print(f"Error: {result.error}")
        else:
            print(f"Output nodes: {list(result.output.keys())}")
        print()
        
        return result.success
    
    except FileNotFoundError:
        print("Example file not found, skipping test")
        return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MINI-N8N WORKFLOW AUTOMATION ENGINE - TEST SUITE")
    print("=" * 60 + "\n")
    
    # Initialize
    print("Initializing database...")
    await init_database()
    
    print("Registering nodes...")
    register_all_nodes()
    print()
    
    # Run tests
    results = []
    
    results.append(("Simple Workflow", await test_simple_workflow()))
    results.append(("Conditional Logic", await test_conditional_workflow()))
    results.append(("HTTP Request", await test_http_workflow()))
    results.append(("Caching", await test_caching()))
    results.append(("JSON Loading", await test_from_json()))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60 + "\n")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)


