"""Guitar Pro MCP Server v2.2.3"""
from .controller import GuitarProController, get_controller
from .server import main

__version__ = "2.2.3"
__all__ = ["GuitarProController", "get_controller", "main"]
