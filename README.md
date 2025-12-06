# Mini-N8N: Python Workflow Automation Engine

A powerful, Opal-like workflow automation engine built in Python with DAG-based orchestration and natural language support.

## Features

- 🔄 **DAG-based Workflow Engine**: Automatic dependency resolution and topological sorting
- 🧩 **Modular Node System**: Dynamic registry with extensible node types
- 🤖 **AI-Powered Nodes**: LLM text generation, image generation, video generation
- 🔗 **Data Flow**: Seamless data passing between nodes with variable interpolation
- 💾 **Persistent Storage**: SQLite/PostgreSQL support with JSON serialization
- 🚀 **FastAPI Backend**: RESTful API for workflow management and execution
- ⚡ **Caching & Performance**: Intelligent caching and async execution
- 📊 **Error Handling**: Comprehensive logging and error recovery

## Project Structure

```
mini-n8n/
├── core/               # Workflow engine and DAG logic
├── nodes/              # Node implementations
├── storage/            # Database and serialization
├── executor/           # Workflow runner and cache
├── api/                # FastAPI routes
├── utils/              # Helper utilities
└── examples/           # Example workflows
```

## Built-in Nodes

- **User Input Node**: Capture user-provided data
- **LLM Text Generation Node**: OpenAI, Anthropic, etc.
- **Image Generation Node**: DALL-E, Stable Diffusion
- **Video Generation Node**: Google Veo integration
- **HTTP Request Node**: External API calls
- **Conditional Logic Node**: If/else workflow branching
- **Output Node**: Return workflow results

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Add your API keys
```

3. Run the server:
```bash
python main.py
```

4. Access API documentation:
```
http://localhost:8000/docs
```

## Example Workflow

```python
{
  "name": "Blog Post Generator",
  "nodes": [
    {
      "id": "input1",
      "type": "user_input",
      "config": {"prompt": "Enter blog topic"}
    },
    {
      "id": "llm1",
      "type": "llm_text_generation",
      "config": {
        "prompt": "Write a blog post about: {{input1.output}}",
        "model": "gpt-4"
      }
    },
    {
      "id": "output1",
      "type": "output",
      "config": {"format": "text"}
    }
  ],
  "connections": [
    {"from": "input1", "to": "llm1"},
    {"from": "llm1", "to": "output1"}
  ]
}
```

## API Endpoints

- `POST /workflows/` - Create a new workflow
- `GET /workflows/{id}` - Get workflow details
- `PUT /workflows/{id}` - Update workflow
- `DELETE /workflows/{id}` - Delete workflow
- `POST /workflows/{id}/execute` - Execute workflow
- `GET /workflows/{id}/executions/{exec_id}` - Get execution results
- `GET /node-types/` - List available node types
- `POST /nodes/{type}/preview` - Preview node execution

## Configuration

Edit `.env` to configure:
- Database connection
- API keys for AI services
- Caching settings
- Execution limits

## License

MIT License - See LICENSE file for details


