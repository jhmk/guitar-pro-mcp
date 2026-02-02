"""Guitar Pro MCP Server v2.0 - Optimized with batch operations."""
from .controller import GuitarProController, get_controller
from .server import main

__version__ = "2.0.0"
__all__ = ["GuitarProController", "get_controller", "main"]
