"""Main entry point for Mini-N8N workflow automation engine."""

import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import app
from api.app import app

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    # Run server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )


