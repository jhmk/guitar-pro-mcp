import os
import sys
from typing import Dict, List, Optional, Union, Any

# Import PyGuitarPro - use the pip-installed package directly
# No need to clone the PyGuitarPro repo separately
try:
    import guitarpro as gp
except ImportError as e:
    print(f"Error importing guitarpro module: {e}")
    print("Install PyGuitarPro with: pip install pyguitarpro")
    raise

from guitarpro.models import (
    Song, Track, Measure, MeasureHeader, Voice, Beat, Note, 
    Duration, TimeSignature, KeySignature, TripletFeel
)

from guitarpro import parse

class GuitarProMixin:
    """Mixin class providing basic Guitar Pro functionality."""
    
    def __init__(self):
        """Initialize the Guitar Pro controller."""
        self.current_song = None
        
    def _ensure_song_loaded(self):
        """Ensure a song is loaded before performing operations."""
        if not self.current_song:
            raise ValueError("No song is currently loaded")
