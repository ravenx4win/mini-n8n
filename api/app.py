"""FastAPI application setup."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from storage.database import init_database
from nodes.registry_setup import register_all_nodes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logging.info("Initializing database...")
    await init_database()
    
    logging.info("Registering node types...")
    register_all_nodes()
    
    logging.info("Application started successfully")
    
    yield
    
    # Shutdown
    logging.info("Application shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Mini-N8N Workflow Automation Engine",
    description="Python-based workflow automation engine with DAG orchestration and AI capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mini-n8n"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Mini-N8N Workflow Automation Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


