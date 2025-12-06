"""FastAPI application and routes."""

from .app import app, lifespan
from .routes import router

__all__ = ["app", "lifespan", "router"]


