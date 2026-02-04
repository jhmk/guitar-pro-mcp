"""
Guitar Pro MCP v3.0

Full-featured Guitar Pro file manipulation via MCP.

Features:
- Read/Write GP3/4/5
- Read GP7/8 (.gp)
- MusicXML Import/Export
- All note effects (bend, trill, harmonic, tremolo, grace notes, etc.)
- Song structure (markers, repeats, tempo changes)
- TAB import, chords, templates, transpose
"""

from .controller import GuitarProController, get_controller

__version__ = "3.0.0"
__all__ = ["GuitarProController", "get_controller"]
