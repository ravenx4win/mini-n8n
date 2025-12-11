"""
FastAPI application setup for Mini-N8N.
Initializes database, registers node types, and configures API with secure CORS + API Key authentication.
"""

from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import logging
import os

from storage.database import init_database
from nodes.registry_setup import register_all_nodes
from api.routes import router  # IMPORTANT: include all API endpoints


# ---------------------------------------------------------------------
# Load Environment Variables (.env)
# ---------------------------------------------------------------------
load_dotenv()

API_KEY = os.getenv("API_KEY")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")


# ---------------------------------------------------------------------
# API Key Authentication Dependency
# ---------------------------------------------------------------------
async def verify_api_key(x_api_key: str = Header(None)):
    """
    Validate incoming requests using x-api-key header.
    Every request MUST include the correct API key.
    """
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# ---------------------------------------------------------------------
# Application Lifespan (Startup + Shutdown)
# ---------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""

    logging.info("🚀 Starting Mini-N8N Engine...")

    # Initialize Database
    try:
        logging.info("Initializing database...")
        await init_database()
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        raise

    # Register all node types
    try:
        logging.info("Registering node types...")
        register_all_nodes()
    except Exception as e:
        logging.error(f"Node registration failed: {e}")
        raise

    logging.info("Mini-N8N started successfully ✔")
    yield
    logging.info("Mini-N8N shutting down...")


# ---------------------------------------------------------------------
# FastAPI Instance Creation
# ---------------------------------------------------------------------
app = FastAPI(
    title="Mini-N8N Workflow Automation Engine",
    description="Python-based workflow automation engine with DAG execution, AI nodes, and workflow orchestration",
    version="1.0.0",
    lifespan=lifespan
)


# ---------------------------------------------------------------------
# Secure CORS Configuration (Using .env)
# ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,           # Secure CORS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Register API Routes — Protected with API Key
# ---------------------------------------------------------------------
app.include_router(router, dependencies=[Depends(verify_api_key)])


# ---------------------------------------------------------------------
# Health Check Route (Public)
# ---------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mini-n8n"}


# ---------------------------------------------------------------------
# Root Endpoint (Public)
# ---------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint providing API metadata."""
    return {
        "name": "Mini-N8N Workflow Automation Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
