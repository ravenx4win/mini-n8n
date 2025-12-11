"""
API package initializer.
Exports the FastAPI app and lifespan handler so external modules can run the server.
"""

from .app import app, lifespan

__all__ = [
    "app",
    "lifespan",
]
