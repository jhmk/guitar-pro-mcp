from guitarpro import parse, write
from .base_controller import GuitarProMixin
import logging

logger = logging.getLogger(__name__)

class FileOperationsController(GuitarProMixin):
    """Controller for Guitar Pro file operations."""
    
    def load_file(self, file_path: str) -> None:
        """Load a Guitar Pro file."""
        try:
            logger.info(f"Loading Guitar Pro file: {file_path}")
            self.current_song = parse(file_path)
            logger.info(f"Loaded: {self.current_song.title} - "
                       f"{len(self.current_song.tracks)} tracks, "
                       f"{len(self.current_song.measureHeaders)} measures")
        except Exception as e:
            logger.error(f"Error loading file: {e}")
            raise
        
    def save_file(self, file_path: str) -> None:
        """
        Save the current song to a Guitar Pro file.
        
        FIX: Explicitly pass version=(5, 1, 0) to ensure GP5 format.
        The original code didn't pass a version, which could cause
        issues when saving newly created songs.
        """
        self._ensure_song_loaded()
        # FIX: Explicitly set GP5 version for reliable saving
        write(self.current_song, file_path, version=(5, 1, 0))
        logger.info(f"Saved Guitar Pro file: {file_path}")
            
    def export_to_midi(self, file_path: str) -> bool:
        """Export the current song to MIDI format."""
        if self.current_song is None:
            print("No song loaded")
            return False
        
        try:
            try:
                from utils.midi_export import convert_to_midi
                return convert_to_midi(self.current_song, file_path)
            except ImportError:
                try:
                    from guitarpro.models import write_midi
                    write_midi(self.current_song, file_path)
                    return True
                except (ImportError, AttributeError):
                    raise ImportError("No MIDI export method available")
        except Exception as e:
            print(f"Error exporting to MIDI: {e}")
            return False
            
    def export_to_json(self, file_path: str) -> bool:
        """Export the current song to a JSON file."""
        if self.current_song is None:
            print("No song loaded")
            return False
        try:
            from utils.json_export import export_to_json
            return export_to_json(self.current_song, file_path)
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
    
    def import_from_json(self, file_path: str) -> bool:
        """Import a song from a JSON file."""
        try:
            from utils.json_export import import_from_json
            import guitarpro as gp
            
            song = import_from_json(file_path, gp)
            if song:
                self.current_song = song
                return True
            return False
        except Exception as e:
            print(f"Error importing from JSON: {e}")
            return False
