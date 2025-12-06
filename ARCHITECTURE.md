# Mini-N8N Architecture

## Overview

Mini-N8N is a Python-based workflow automation engine inspired by Google Opal and n8n. It uses a DAG (Directed Acyclic Graph) architecture with node-based orchestration to execute complex workflows.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Layer                         │
│  ┌──────────┬──────────┬──────────┬─────────────────────┐  │
│  │ Workflows│Executions│Node Types│    Health/Docs      │  │
│  └──────────┴──────────┴──────────┴─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                       Core Engine                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Workflow Engine                                       │ │
│  │  • DAG Construction                                    │ │
│  │  • Topological Sorting                                 │ │
│  │  • Dependency Resolution                               │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Executor                                              │ │
│  │  • Node Execution                                      │ │
│  │  • Context Management                                  │ │
│  │  • Caching & Performance                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                       Node System                            │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │  Input   │   LLM    │  Image   │  Video   │   HTTP   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
│  ┌──────────┬──────────┬──────────────────────────────┐    │
│  │Conditional│ Output  │   Custom Nodes (Extensible)  │    │
│  └──────────┴──────────┴──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Storage Layer                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Database (SQLite/PostgreSQL)                          │ │
│  │  • Workflows                                           │ │
│  │  • Executions                                          │ │
│  │  • Results & Logs                                      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
mini-n8n/
├── core/                   # Workflow engine core
│   ├── workflow.py         # Workflow data structures
│   ├── dag.py              # DAG and topological sorting
│   └── registry.py         # Node type registry
│
├── nodes/                  # Node implementations
│   ├── base.py             # Base node class
│   ├── input_node.py       # User input
│   ├── llm_node.py         # LLM text generation
│   ├── image_node.py       # Image generation
│   ├── video_node.py       # Video generation
│   ├── http_node.py        # HTTP requests
│   ├── conditional_node.py # Conditional logic
│   ├── output_node.py      # Output formatting
│   └── registry_setup.py   # Register all nodes
│
├── executor/               # Workflow execution
│   ├── engine.py           # Execution engine
│   └── cache.py            # Result caching
│
├── storage/                # Persistence layer
│   ├── database.py         # Database operations
│   ├── models.py           # SQLAlchemy models
│   └── serialization.py    # JSON serialization
│
├── api/                    # FastAPI application
│   ├── app.py              # Application setup
│   └── routes.py           # API endpoints
│
├── utils/                  # Utilities
│   └── template.py         # Variable interpolation
│
├── examples/               # Example workflows
│   ├── blog_writer.json
│   ├── image_generator.json
│   ├── data_enrichment.json
│   └── video_creator.json
│
└── main.py                 # Entry point
```

## Core Components

### 1. Workflow Engine (`core/`)

**Workflow (`workflow.py`)**
- Data structures for workflows, nodes, and connections
- Validation and manipulation methods
- Serialization to/from dictionaries

**DAG (`dag.py`)**
- Directed Acyclic Graph implementation
- Cycle detection
- Dependency tracking
- Topological sorting using Kahn's algorithm
- Execution level grouping for parallelization

**Registry (`registry.py`)**
- Singleton pattern for node type management
- Dynamic node registration
- Node metadata and schemas
- Node instantiation

### 2. Node System (`nodes/`)

**Base Node (`base.py`)**
- Abstract base class for all nodes
- Standard interface: `run()`, `get_input_schema()`, `get_output_schema()`, `get_config_schema()`
- Configuration validation
- Logging utilities

**Node Types**
Each node type implements:
- Async `run()` method for execution
- Input/output schemas (JSON Schema)
- Configuration schema
- Error handling

### 3. Executor (`executor/`)

**Execution Engine (`engine.py`)**
- Workflow validation
- DAG construction from connections
- Topological sort for execution order
- Sequential node execution
- Context management
- Result aggregation
- Error handling and recovery

**Cache (`cache.py`)**
- In-memory result caching
- TTL-based expiration
- Cache key generation from node config + inputs
- Hit/miss statistics

### 4. Storage (`storage/`)

**Database (`database.py`)**
- Async SQLAlchemy operations
- Workflow CRUD operations
- Execution tracking
- Query methods

**Models (`models.py`)**
- SQLAlchemy ORM models
- Workflow and Execution tables
- Enum types for execution status

**Serialization (`serialization.py`)**
- JSON encoding/decoding
- File I/O operations

### 5. API (`api/`)

**Application (`app.py`)**
- FastAPI setup
- CORS configuration
- Lifespan management (startup/shutdown)
- Database initialization
- Node registration

**Routes (`routes.py`)**
- RESTful API endpoints
- Request/response models (Pydantic)
- Background task execution
- Error handling

## Execution Flow

### 1. Workflow Creation

```
User → POST /api/v1/workflows/
  ↓
Validate nodes and connections
  ↓
Save to database
  ↓
Return workflow ID
```

### 2. Workflow Execution

```
User → POST /api/v1/workflows/{id}/execute
  ↓
Create execution record
  ↓
Queue background task
  ↓
Return execution ID (immediate response)

Background:
  ↓
Load workflow from database
  ↓
Build DAG from connections
  ↓
Perform topological sort
  ↓
For each node in order:
    ├─ Collect inputs from previous nodes
    ├─ Check cache
    ├─ Execute node.run()
    ├─ Store result
    └─ Update context
  ↓
Extract final output
  ↓
Save execution result
```

### 3. Result Retrieval

```
User → GET /api/v1/workflows/{id}/executions/{exec_id}
  ↓
Query database
  ↓
Return execution status, output, and metadata
```

## Data Flow

### Variable Interpolation

```python
# Template string
"Generate blog about: {{input1.output}}"

# Context
{
    "input1": {"output": "AI in Healthcare"},
    "topic": "Healthcare"
}

# Result
"Generate blog about: AI in Healthcare"
```

### Node Output Chaining

```
Input Node (id: input1)
  output: {"output": "Healthcare", "value": "Healthcare"}
    ↓
LLM Node (id: llm1)
  config: {"prompt": "Write about {{input1.output}}"}
  output: {"text": "...", "output": "..."}
    ↓
Output Node (id: output1)
  output: {"output": {...}, "result": {...}}
```

## Scalability Considerations

### Current Implementation
- In-memory caching
- Background async execution
- SQLite for development

### Production Enhancements
- **Caching**: Replace with Redis
- **Message Queue**: Add Celery with Redis/RabbitMQ
- **Database**: Use PostgreSQL
- **Horizontal Scaling**: Stateless API servers
- **Monitoring**: Add Prometheus/Grafana
- **Rate Limiting**: Add per-user quotas

## Extension Points

### 1. Custom Nodes

```python
from nodes.base import BaseNode, NodeResult

class CustomNode(BaseNode):
    async def run(self, inputs, context):
        # Custom logic
        return self.create_result(output=result)
    
    @classmethod
    def get_config_schema(cls):
        return {...}
```

### 2. Custom Storage

Implement custom storage backend by extending `Database` class.

### 3. Authentication

Add middleware to `api/app.py` for JWT/OAuth authentication.

### 4. Custom Executors

Implement custom execution strategies (parallel, distributed, etc.).

## Security Considerations

1. **API Keys**: Stored in environment variables, never in code
2. **Input Validation**: Pydantic models validate all inputs
3. **SQL Injection**: SQLAlchemy ORM prevents injection
4. **Rate Limiting**: Should be added for production
5. **Authentication**: Should be added for production
6. **CORS**: Configure appropriately for your domain

## Performance Optimization

### Caching Strategy
- Cache node results based on config + inputs
- Configurable TTL per node type
- Automatic cleanup of expired entries

### Async Execution
- All I/O operations are async
- Non-blocking API responses
- Background task processing

### Database Optimization
- Indexes on workflow_id, execution_id
- Efficient JSON queries
- Connection pooling

## Testing Strategy

1. **Unit Tests**: Test individual nodes and components
2. **Integration Tests**: Test workflow execution end-to-end
3. **API Tests**: Test REST endpoints
4. **Load Tests**: Test under concurrent load

See `test_workflow.py` for examples.

## Future Enhancements

1. **Parallel Execution**: Execute independent nodes in parallel
2. **Workflow Versioning**: Track workflow changes over time
3. **Workflow Templates**: Reusable workflow templates
4. **Visual Editor**: Web-based drag-and-drop interface
5. **Webhooks**: Trigger workflows via webhooks
6. **Scheduling**: Cron-based workflow scheduling
7. **Monitoring**: Real-time execution monitoring
8. **Permissions**: Role-based access control
9. **Audit Logs**: Track all system operations
10. **Export/Import**: Share workflows between instances


