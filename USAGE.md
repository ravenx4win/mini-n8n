# Mini-N8N Usage Guide

## Getting Started

### 1. Installation

```bash
# Clone or navigate to the project
cd mini-n8n

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Configuration

Edit `.env` and add your API keys:

```bash
# Required for LLM nodes
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Required for image/video generation
REPLICATE_API_TOKEN=r8_...

# Optional for Google Veo (when available)
GOOGLE_API_KEY=...

# Database (default is SQLite)
DATABASE_URL=sqlite:///./workflows.db
```

### 3. Start the Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

Visit `http://localhost:8000/docs` for interactive API documentation.

## Creating Your First Workflow

### Method 1: Using the API

```python
import requests

# Create a simple workflow
workflow = {
    "name": "My First Workflow",
    "description": "A simple text generation workflow",
    "nodes": [
        {
            "id": "input1",
            "type": "user_input",
            "config": {
                "prompt": "Enter a topic",
                "input_key": "topic"
            }
        },
        {
            "id": "llm1",
            "type": "llm_text_generation",
            "config": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": "Write a short paragraph about: {{input1.output}}",
                "temperature": 0.7,
                "max_tokens": 200
            }
        },
        {
            "id": "output1",
            "type": "output",
            "config": {
                "format": "text"
            }
        }
    ],
    "connections": [
        {"from_node": "input1", "to_node": "llm1"},
        {"from_node": "llm1", "to_node": "output1"}
    ]
}

# Create workflow
response = requests.post(
    "http://localhost:8000/api/v1/workflows/",
    json=workflow
)
workflow_id = response.json()["id"]
print(f"Created workflow: {workflow_id}")
```

### Method 2: Using Example Workflows

Load and run example workflows:

```python
import json
import requests

# Load example
with open("examples/blog_writer.json") as f:
    workflow = json.load(f)

# Create workflow
response = requests.post(
    "http://localhost:8000/api/v1/workflows/",
    json=workflow
)
workflow_id = response.json()["id"]

# Execute workflow
response = requests.post(
    f"http://localhost:8000/api/v1/workflows/{workflow_id}/execute",
    json={
        "input_data": {
            "topic": "The Future of AI in Healthcare"
        }
    }
)
execution_id = response.json()["execution_id"]

# Get results (wait a few seconds for execution to complete)
import time
time.sleep(5)

response = requests.get(
    f"http://localhost:8000/api/v1/workflows/{workflow_id}/executions/{execution_id}"
)
print(response.json()["output_data"])
```

## Available Nodes

### 1. User Input Node

Captures user-provided data.

```json
{
  "type": "user_input",
  "config": {
    "prompt": "Enter a value",
    "input_key": "my_input",
    "default": "default value",
    "type": "text"
  }
}
```

### 2. LLM Text Generation Node

Generates text using AI models.

```json
{
  "type": "llm_text_generation",
  "config": {
    "provider": "openai",
    "model": "gpt-4",
    "prompt": "Write about {{input.value}}",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**Supported providers:**
- `openai` - GPT-3.5, GPT-4, etc.
- `anthropic` - Claude models

### 3. Image Generation Node

Creates images using AI.

```json
{
  "type": "image_generation",
  "config": {
    "provider": "openai",
    "model": "dall-e-3",
    "prompt": "A beautiful {{input.subject}}",
    "size": "1024x1024",
    "quality": "hd"
  }
}
```

**Supported providers:**
- `openai` - DALL-E 2, DALL-E 3
- `replicate` - Stable Diffusion and others

### 4. Video Generation Node

Generates videos from text.

```json
{
  "type": "video_generation",
  "config": {
    "provider": "replicate",
    "model": "zeroscope-v2-xl",
    "prompt": "{{llm.description}}",
    "duration": 3,
    "fps": 24
  }
}
```

### 5. HTTP Request Node

Makes API calls.

```json
{
  "type": "http_request",
  "config": {
    "method": "GET",
    "url": "https://api.example.com/data/{{id}}",
    "headers": {
      "Authorization": "Bearer {{token}}"
    },
    "timeout": 30
  }
}
```

### 6. Conditional Logic Node

Implements branching logic.

```json
{
  "type": "conditional_logic",
  "config": {
    "condition_type": "equals",
    "value1": "{{node1.output}}",
    "value2": "expected_value"
  }
}
```

**Condition types:**
- `equals`, `not_equals`
- `greater_than`, `less_than`
- `contains`, `not_contains`
- `starts_with`, `ends_with`
- `is_empty`, `is_not_empty`

### 7. Output Node

Returns final results.

```json
{
  "type": "output",
  "config": {
    "format": "json",
    "fields": ["node1.output", "node2.text"]
  }
}
```

## Variable Interpolation

Use `{{variable}}` syntax to reference data:

```
{{input_node_id.output}}          # Access node output
{{node_id.field_name}}             # Access specific field
{{node_id.nested.field}}           # Access nested data
{{variable_from_context}}          # Access context variable
```

## Example Use Cases

### 1. Blog Post Generator

See `examples/blog_writer.json`

Creates complete blog posts from topics using multi-step AI generation.

### 2. Social Media Content Creator

```python
workflow = {
    "name": "Social Media Post",
    "nodes": [
        {"id": "input", "type": "user_input", ...},
        {"id": "llm_post", "type": "llm_text_generation", ...},
        {"id": "image", "type": "image_generation", ...},
        {"id": "output", "type": "output", ...}
    ]
}
```

### 3. Data Processing Pipeline

See `examples/data_enrichment.json`

Fetches data from APIs, enriches with AI, and applies conditional logic.

### 4. Multi-Modal Content Generator

Combines text, images, and videos in a single workflow.

## Advanced Features

### Caching

Execution results are automatically cached to improve performance:

```python
# Disable caching for a specific execution
requests.post(
    f"http://localhost:8000/api/v1/workflows/{workflow_id}/execute",
    json={"input_data": {...}, "use_cache": False}
)
```

### Background Execution

Workflows execute asynchronously. Poll for results:

```python
def wait_for_execution(workflow_id, execution_id):
    while True:
        response = requests.get(
            f"http://localhost:8000/api/v1/workflows/{workflow_id}/executions/{execution_id}"
        )
        status = response.json()["status"]
        if status in ["success", "failed"]:
            return response.json()
        time.sleep(1)
```

### Node Preview

Test nodes before adding to workflows:

```python
response = requests.post(
    "http://localhost:8000/api/v1/nodes/llm_text_generation/preview",
    json={
        "type": "llm_text_generation",
        "config": {
            "provider": "openai",
            "model": "gpt-4",
            "prompt": "Say hello",
            "max_tokens": 50
        },
        "inputs": {},
        "context": {}
    }
)
print(response.json())
```

## API Reference

### Workflows

- `POST /api/v1/workflows/` - Create workflow
- `GET /api/v1/workflows/{id}` - Get workflow
- `GET /api/v1/workflows/` - List workflows
- `PUT /api/v1/workflows/{id}` - Update workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow

### Executions

- `POST /api/v1/workflows/{id}/execute` - Execute workflow
- `GET /api/v1/workflows/{id}/executions/{exec_id}` - Get execution
- `GET /api/v1/workflows/{id}/executions/` - List executions

### Node Types

- `GET /api/v1/node-types/` - List all node types
- `GET /api/v1/node-types/{type}` - Get node type details
- `POST /api/v1/nodes/{type}/preview` - Preview node execution

## Troubleshooting

### API Key Errors

```
Error: OPENAI_API_KEY not set
```

**Solution:** Add your API key to `.env` file.

### Import Errors

```
ModuleNotFoundError: No module named 'openai'
```

**Solution:** Install dependencies: `pip install -r requirements.txt`

### Database Errors

```
Error: table workflows does not exist
```

**Solution:** Database tables are created automatically on startup. Restart the server.

### Workflow Validation Errors

```
Invalid workflow structure: Connection references non-existent node
```

**Solution:** Ensure all connections reference valid node IDs.

## Next Steps

1. Explore the example workflows in `examples/`
2. Create custom node types by extending `BaseNode`
3. Integrate with frontend workflow builder
4. Add authentication and user management
5. Deploy to production with PostgreSQL and Redis

For more information, visit the [API documentation](http://localhost:8000/docs).


