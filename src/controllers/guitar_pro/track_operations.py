from typing import Dict, List, Any
from .base_controller import GuitarProMixin
import guitarpro as gp
from guitarpro.models import Song, Track, Measure, Voice, Beat, Duration
import logging

logger = logging.getLogger(__name__)

class TrackOperationsController(GuitarProMixin):
    """Controller for Guitar Pro track operations."""
    
    def get_tracks(self) -> List[Dict[str, Any]]:
        """
        Get a list of tracks in the song.
        
        Returns:
            list: List of track information
        """
        if self.current_song is None:
            return []
            
        return [
            {
                "name": track.name,
                "index": i,
                "strings": len(track.strings),
                "instrument": track.channel.instrument,
                "is_percussion": track.isPercussionTrack
            }
            for i, track in enumerate(self.current_song.tracks)
        ]
        
    def get_track_notes(self, track_index: int) -> List[Dict[str, Any]]:
        """
        Get all notes from a specific track.
        
        Args:
            track_index (int): Index of the track
            
        Returns:
            list: List of notes with their properties
        """
        if self.current_song is None:
            logger.warning("No song loaded")
            return []
            
        if track_index < 0 or track_index >= len(self.current_song.tracks):
            logger.warning(f"Invalid track index: {track_index}")
            return []
            
        track = self.current_song.tracks[track_index]
        notes = []
        
        for measure_index, measure in enumerate(track.measures):
            for voice_index, voice in enumerate(measure.voices):
                for beat_index, beat in enumerate(voice.beats):
                    for note in beat.notes:
                        note_info = {
                            "measure": measure_index,
                            "voice": voice_index,
                            "beat": beat_index,
                            "string": note.string,
                            "value": note.value,
                            "duration": beat.duration.value,
                            "is_dotted": beat.duration.isDotted,
                            "has_tie": note.isTiedNote
                        }
                        notes.append(note_info)
        
        logger.info(f"Total notes found in track {track_index}: {len(notes)}")
        return notes
        
    def add_track(self, name: str) -> int:
        """
        Add a new track to the song.
        
        Args:
            name (str): Name of the track
            
        Returns:
            int: Index of the new track
        """
        if self.current_song is None:
            self.current_song = Song()
            self.current_song.title = "New Song"
        
        # FIX: Use the existing default track structure from Song() 
        # instead of creating a broken track from scratch.
        # Track() constructor already creates proper 6-string standard tuning.
        track = Track(self.current_song)
        track.name = name
        track.channel.instrument = 25  # Overdriven Guitar
        
        # FIX: Do NOT append extra strings! Track() already has 6 strings 
        # in standard tuning (E2, A2, D3, G3, B3, E4).
        # The original code appended 6 MORE strings to the existing 6, 
        # resulting in 12 strings which Guitar Pro can't handle.
        
        # Create measures to match existing measure headers
        for header in self.current_song.measureHeaders:
            measure = Measure(track, header)
            # Voices are created automatically by Measure constructor
            track.measures.append(measure)
            
        self.current_song.tracks.append(track)
        return len(self.current_song.tracks) - 1
        
    def set_track_properties(self, track_index: int, name: str = None,
                           instrument: int = None, volume: int = None,
                           pan: int = None) -> bool:
        """
        Set properties of a track.
        
        Args:
            track_index (int): Index of the track
            name (str, optional): Name of the track
            instrument (int, optional): MIDI instrument number (0-127)
            volume (int, optional): Volume (0-100)
            pan (int, optional): Pan (-64 to 63)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.current_song is None:
            print("No song loaded")
            return False
            
        if track_index < 0 or track_index >= len(self.current_song.tracks):
            print(f"Invalid track index: {track_index}")
            return False
            
        try:
            track = self.current_song.tracks[track_index]
            
            if name is not None:
                track.name = name
                
            if instrument is not None:
                if 0 <= instrument <= 127:
                    track.channel.instrument = instrument
                else:
                    print("Instrument must be between 0 and 127")
                    return False
                    
            if volume is not None:
                if 0 <= volume <= 100:
                    track.channel.volume = volume
                else:
                    print("Volume must be between 0 and 100")
                    return False
                    
            if pan is not None:
                if -64 <= pan <= 63:
                    track.channel.balance = pan
                else:
                    print("Pan must be between -64 and 63")
                    return False
                    
            return True
        except Exception as e:
            print(f"Error setting track properties: {e}")
            return False
            
    def transpose_track(self, track_index: int, semitones: int) -> bool:
        """
        Transpose all notes in a track by a specified number of semitones.
        
        Args:
            track_index (int): Index of the track to transpose
            semitones (int): Number of semitones to transpose (positive = up, negative = down)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.current_song is None:
            print("No song loaded")
            return False
            
        if track_index < 0 or track_index >= len(self.current_song.tracks):
            print(f"Invalid track index: {track_index}")
            return False
            
        try:
            track = self.current_song.tracks[track_index]
            
            for measure in track.measures:
                for voice in measure.voices:
                    for beat in voice.beats:
                        for note in beat.notes:
                            if note.isTiedNote:
                                continue
                                
                            string_obj = None
                            for s in track.strings:
                                if s.number == note.string:
                                    string_obj = s
                                    break
                            
                            if string_obj is None:
                                continue
                                
                            current_pitch = string_obj.value + note.value
                            new_pitch = current_pitch + semitones
                            new_fret = new_pitch - string_obj.value
                            
                            if new_fret >= 0:
                                note.value = new_fret
                            
            return True
        except Exception as e:
            print(f"Error transposing track: {e}")
            return False
            
    def get_track_tab(self, track_index: int) -> str:
        """
        Generate an ASCII tab representation of a track.
        
        Args:
            track_index (int): Index of the track
            
        Returns:
            str: ASCII tab representation
        """
        if self.current_song is None:
            return "No song loaded"
            
        if track_index < 0 or track_index >= len(self.current_song.tracks):
            return f"Invalid track index: {track_index}"
            
        track = self.current_song.tracks[track_index]
        tab_lines = []
        
        strings = track.strings
        if not strings:
            return "No strings in track"
            
        tab_lines.append(f"Track: {track.name}")
        tab_lines.append("")
        tab_lines.append("Tuning: " + " ".join([self._note_from_value(s.value) for s in sorted(strings, key=lambda s: s.number)]))
        tab_lines.append("")
        
        string_lines = ["" for _ in range(len(strings))]
        
        for measure_index, measure in enumerate(track.measures):
            measure_header = f"|-{measure_index + 1}-"
            for string_index in range(len(strings)):
                string_lines[string_index] += measure_header
            
            max_measure_width = len(measure_header)
            
            for voice in measure.voices:
                voice_width = 0
                temp_string_lines = ["" for _ in range(len(strings))]
                
                for beat in voice.beats:
                    for i in range(len(strings)):
                        temp_string_lines[i] += "-"
                    
                    for note in beat.notes:
                        string_index = len(strings) - note.string
                        
                        if 0 <= string_index < len(strings):
                            fret_str = str(note.value)
                            temp_string_lines[string_index] = temp_string_lines[string_index][:-1] + fret_str
                            
                            fret_len = len(fret_str)
                            if fret_len > 1:
                                for i in range(len(strings)):
                                    if i != string_index:
                                        temp_string_lines[i] += "-" * (fret_len - 1)
                    
                    duration_space = 1
                    for i in range(len(strings)):
                        temp_string_lines[i] += "-" * duration_space
                    
                    voice_width += 1 + duration_space
                
                max_measure_width = max(max_measure_width, voice_width)
                
                for i in range(len(strings)):
                    string_lines[i] += temp_string_lines[i]
            
            for i in range(len(strings)):
                string_lines[i] += "|"
            
            if (measure_index + 1) % 4 == 0:
                tab_lines.extend(string_lines)
                tab_lines.append("")
                string_lines = ["" for _ in range(len(strings))]
        
        if any(line for line in string_lines):
            tab_lines.extend(string_lines)
        
        return "\n".join(tab_lines)
        
    def _note_from_value(self, value: int) -> str:
        """Convert a MIDI note value to note name."""
        notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = value // 12 - 1
        note = value % 12
        return f"{notes[note]}{octave}"
