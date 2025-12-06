# 🚀 Get Started with Mini-N8N

## Welcome! 

You now have a complete, production-ready workflow automation engine that works just like Google Opal!

## ⚡ Quick Start (5 minutes)

### Step 1: Install Dependencies

```bash
# Using the quick start script
chmod +x quickstart.sh
./quickstart.sh

# OR manually:
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Configure API Keys

Create a `.env` file (or copy from `.env.example`):

```bash
# Required for LLM text generation
OPENAI_API_KEY=sk-your-key-here

# Optional: For Claude models
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: For image/video generation
REPLICATE_API_TOKEN=r8_your-token-here

# Database (default works out of the box)
DATABASE_URL=sqlite:///./workflows.db
```

### Step 3: Start the Server

```bash
python main.py
```

You should see:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 4: Test the API

Open your browser and visit:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🎯 Your First Workflow (Python)

Create a simple workflow using Python:

```python
import requests
import json
import time

# 1. Create a workflow
workflow = {
    "name": "Simple Hello World",
    "nodes": [
        {
            "id": "input1",
            "type": "user_input",
            "config": {
                "input_key": "name",
                "default": "World"
            }
        },
        {
            "id": "llm1",
            "type": "llm_text_generation",
            "config": {
                "provider": "openai",
                "model": "gpt-4",
                "prompt": "Say hello to {{input1.output}} in a creative way!",
                "temperature": 0.8,
                "max_tokens": 100
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

# 2. Create the workflow
response = requests.post(
    "http://localhost:8000/api/v1/workflows/",
    json=workflow
)
workflow_id = response.json()["id"]
print(f"✓ Created workflow: {workflow_id}")

# 3. Execute it
response = requests.post(
    f"http://localhost:8000/api/v1/workflows/{workflow_id}/execute",
    json={"input_data": {"name": "Alice"}}
)
execution_id = response.json()["execution_id"]
print(f"✓ Started execution: {execution_id}")

# 4. Wait for completion and get results
time.sleep(3)  # Give it time to complete

response = requests.get(
    f"http://localhost:8000/api/v1/workflows/{workflow_id}/executions/{execution_id}"
)
result = response.json()

print(f"\n{'='*50}")
print(f"Status: {result['status']}")
print(f"Output: {result['output_data']}")
print(f"Execution Time: {result['execution_time']:.2f}s")
print(f"{'='*50}\n")
```

Save this as `test_hello.py` and run:

```bash
python test_hello.py
```

## 📖 Try Example Workflows

### Example 1: Blog Post Generator

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

# Execute with your topic
response = requests.post(
    f"http://localhost:8000/api/v1/workflows/{workflow_id}/execute",
    json={
        "input_data": {
            "topic": "The Future of Artificial Intelligence"
        }
    }
)

print(f"Generating blog post... Execution ID: {response.json()['execution_id']}")
```

### Example 2: Image Generator

```python
import json
import requests

with open("examples/image_generator.json") as f:
    workflow = json.load(f)

response = requests.post("http://localhost:8000/api/v1/workflows/", json=workflow)
workflow_id = response.json()["id"]

response = requests.post(
    f"http://localhost:8000/api/v1/workflows/{workflow_id}/execute",
    json={
        "input_data": {
            "description": "A serene mountain landscape at sunset"
        }
    }
)

print(f"Generating image... Execution ID: {response.json()['execution_id']}")
```

## 🧪 Run Tests

Verify everything works:

```bash
python test_workflow.py
```

You should see all tests passing:

```
✓ PASSED: Simple Workflow
✓ PASSED: Conditional Logic
✓ PASSED: HTTP Request
✓ PASSED: Caching
✓ PASSED: JSON Loading

🎉 All tests passed!
```

## 🎨 Understanding the System

### What Just Happened?

When you created and executed a workflow:

1. **Workflow Creation**: Your workflow definition was validated and saved to SQLite
2. **DAG Construction**: The system built a directed graph from your connections
3. **Topological Sort**: Nodes were ordered for correct execution
4. **Async Execution**: Each node ran asynchronously in the background
5. **Context Passing**: Outputs from each node were passed to the next
6. **Caching**: Results were cached for faster re-execution

### The Magic of Variable Interpolation

When you write:
```json
"prompt": "Say hello to {{input1.output}}"
```

The system:
1. Finds `input1` in executed nodes
2. Extracts the `output` field
3. Replaces the placeholder with the actual value
4. Sends the final prompt to the LLM

### Node Execution Flow

```
Start → Validate → Build DAG → Sort → Execute Nodes → Cache → Return
```

Each node:
- Receives inputs from previous nodes
- Processes them according to its type
- Returns a result (output, error, metadata)
- Result is cached for next time

## 🔍 Explore the API

### List All Node Types

```bash
curl http://localhost:8000/api/v1/node-types/
```

You'll see all 7 built-in nodes with their schemas.

### Preview a Node (Without Saving)

```bash
curl -X POST http://localhost:8000/api/v1/nodes/llm_text_generation/preview \
  -H "Content-Type: application/json" \
  -d '{
    "type": "llm_text_generation",
    "config": {
      "provider": "openai",
      "model": "gpt-4",
      "prompt": "Write a haiku about coding",
      "max_tokens": 100
    },
    "inputs": {},
    "context": {}
  }'
```

### List Your Workflows

```bash
curl http://localhost:8000/api/v1/workflows/
```

## 📚 Next Steps

### 1. Read the Documentation

- **README.md** - Project overview
- **USAGE.md** - Detailed usage guide
- **ARCHITECTURE.md** - System architecture
- **FEATURES.md** - Feature showcase
- **PROJECT_SUMMARY.md** - Complete summary

### 2. Explore Example Workflows

Check out the `examples/` directory:
- `blog_writer.json` - Multi-step content creation
- `image_generator.json` - AI image generation
- `data_enrichment.json` - API + AI processing
- `video_creator.json` - Video generation pipeline

### 3. Build Your Own Workflows

Ideas to try:
- **Social Media Bot**: Generate posts with images
- **Data Analyzer**: Fetch data → analyze → visualize
- **Content Moderator**: Check text → classify → action
- **Newsletter Generator**: Fetch news → summarize → format
- **Code Generator**: Requirements → code → documentation

### 4. Create Custom Nodes

Extend the system with your own nodes:

```python
from nodes.base import BaseNode, NodeResult

class MyCustomNode(BaseNode):
    async def run(self, inputs, context):
        # Your logic here
        result = do_something()
        return self.create_result(output=result)
    
    @classmethod
    def get_config_schema(cls):
        return {
            "type": "object",
            "properties": {
                "my_config": {"type": "string"}
            }
        }
    
    @classmethod
    def get_input_schema(cls):
        return {"type": "object"}
    
    @classmethod
    def get_output_schema(cls):
        return {"type": "object"}
```

Register it:

```python
from core.registry import registry
registry.register("my_custom_node", MyCustomNode, ...)
```

### 5. Build a Frontend

The API is ready for a visual builder! Consider:
- React Flow for node-based UI
- Vue Flow for Vue.js
- Rete.js for vanilla JavaScript

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'openai'"

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Problem: "OPENAI_API_KEY not set"

**Solution**: Add your API key to `.env`
```bash
echo "OPENAI_API_KEY=sk-your-key" >> .env
```

### Problem: "Connection refused"

**Solution**: Make sure the server is running
```bash
python main.py
```

### Problem: "Workflow execution failed"

**Solution**: Check the execution details
```bash
curl http://localhost:8000/api/v1/workflows/{id}/executions/{exec_id}
```

Look at the `error` field for details.

## 💡 Pro Tips

1. **Use Caching**: Set `use_cache: true` to speed up repeated executions
2. **Test Nodes**: Use the preview endpoint to test nodes before adding to workflows
3. **Check Logs**: Server logs show detailed execution information
4. **Monitor Cache**: Check cache stats to optimize performance
5. **Version Workflows**: The system tracks workflow versions automatically

## 🎉 You're Ready!

You now have a complete workflow automation engine. Start building amazing AI-powered workflows!

### Quick Commands

```bash
# Start server
python main.py

# Run tests
python test_workflow.py

# Make executable and run quick start
chmod +x quickstart.sh
./quickstart.sh
```

### Important URLs

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🤝 Need Help?

1. Check the documentation files
2. Review example workflows
3. Run the test suite
4. Check server logs
5. Try the interactive API docs

---

**Happy Workflow Building!** 🚀

Built with ❤️ using Python, FastAPI, and AI


