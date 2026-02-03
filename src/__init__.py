"""Guitar Pro MCP Server v3.0"""
from .controller import GuitarProController, get_controller
from .server import main

__version__ = "3.0.0"
__all__ = ["GuitarProController", "get_controller", "main"]
