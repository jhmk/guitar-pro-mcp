"""
Optimized Guitar Pro Controller v2.0
- Single controller class (no complex mixin inheritance)
- Batch operations for speed
- Built-in tuning presets
- Chord helpers
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

import guitarpro as gp
from guitarpro import parse, write
from guitarpro.models import (
    Song, Track, Measure, MeasureHeader, Voice, Beat, Note,
    Duration, TimeSignature, KeySignature, GuitarString
)

logger = logging.getLogger(__name__)

# =============================================================================
# TUNING PRESETS
# =============================================================================

TUNINGS = {
    # Standard tunings (values are MIDI note numbers, low to high string)
    "standard":     [40, 45, 50, 55, 59, 64],  # E2 A2 D3 G3 B3 E4
    "drop_d":       [38, 45, 50, 55, 59, 64],  # D2 A2 D3 G3 B3 E4
    "drop_c":       [36, 43, 48, 53, 57, 62],  # C2 G2 C3 F3 A3 D4
    "drop_b":       [35, 42, 47, 52, 56, 61],  # B1 F#2 B2 E3 G#3 C#4
    "drop_a":       [33, 40, 45, 50, 54, 59],  # A1 E2 A2 D3 F#3 B3
    "d_standard":   [38, 43, 48, 53, 57, 62],  # D2 G2 C3 F3 A3 D4
    "c_standard":   [36, 41, 46, 51, 55, 60],  # C2 F2 Bb2 Eb3 G3 C4
    "open_d":       [38, 45, 50, 54, 57, 62],  # D2 A2 D3 F#3 A3 D4
    "open_g":       [38, 43, 50, 55, 59, 62],  # D2 G2 D3 G3 B3 D4
    "dadgad":       [38, 45, 50, 55, 57, 62],  # D2 A2 D3 G3 A3 D4
    # 7-string
    "standard_7":   [35, 40, 45, 50, 55, 59, 64],  # B1 E2 A2 D3 G3 B3 E4
    "drop_a_7":     [33, 40, 45, 50, 55, 59, 64],  # A1 E2 A2 D3 G3 B3 E4
    # Bass
    "bass_standard": [28, 33, 38, 43],  # E1 A1 D2 G2
    "bass_drop_d":   [26, 33, 38, 43],  # D1 A1 D2 G2
    "bass_5_standard": [23, 28, 33, 38, 43],  # B0 E1 A1 D2 G2
}

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# =============================================================================
# MAIN CONTROLLER
# =============================================================================

class GuitarProController:
    """
    Unified Guitar Pro controller with optimized batch operations.
    """
    
    def __init__(self):
        self.song: Optional[Song] = None
        
    # -------------------------------------------------------------------------
    # FILE OPERATIONS
    # -------------------------------------------------------------------------
    
    def load(self, path: str) -> Dict[str, Any]:
        """Load a Guitar Pro file."""
        self.song = parse(path)
        return self.get_info()
    
    def save(self, path: str) -> bool:
        """Save to Guitar Pro 5 format."""
        if not self.song:
            raise ValueError("No song loaded")
        write(self.song, path, version=(5, 1, 0))
        return True
    
    # -------------------------------------------------------------------------
    # SONG OPERATIONS
    # -------------------------------------------------------------------------
    
    def create(self, title: str = "New Song", artist: str = "", 
               tempo: int = 120, tuning: str = "standard") -> Dict[str, Any]:
        """
        Create a new song with sensible defaults.
        Returns song info.
        """
        self.song = Song()
        self.song.title = title
        self.song.artist = artist
        self.song.tempo = tempo
        
        # Configure default track with tuning
        if self.song.tracks:
            track = self.song.tracks[0]
            track.name = "Guitar"
            track.channel.instrument = 25  # Overdriven Guitar
            self._set_track_tuning(track, tuning)
        
        return self.get_info()
    
    def create_complete(self, title: str, artist: str = "", tempo: int = 120,
                        tracks: List[Dict] = None, measures: int = 4,
                        notes: List[Dict] = None) -> Dict[str, Any]:
        """
        Create a complete song in ONE call.
        
        Args:
            title: Song title
            artist: Artist name
            tempo: BPM
            tracks: List of track configs [{"name": "Lead", "tuning": "drop_d"}, ...]
            measures: Number of measures to create
            notes: List of note dicts for batch adding
            
        Returns:
            Complete song info
        """
        # Create base song
        self.song = Song()
        self.song.title = title
        self.song.artist = artist
        self.song.tempo = tempo
        
        # Setup tracks
        if tracks:
            # Configure first track, add more if needed
            for i, t in enumerate(tracks):
                if i == 0:
                    # Use existing default track
                    track = self.song.tracks[0]
                else:
                    # Create additional tracks
                    track = Track(self.song)
                    self.song.tracks.append(track)
                track.name = t.get("name", f"Track {i+1}")
                track.channel.instrument = t.get("instrument", 25)
                self._set_track_tuning(track, t.get("tuning", "standard"))
                # Ensure track has measures matching headers
                while len(track.measures) < len(self.song.measureHeaders):
                    header = self.song.measureHeaders[len(track.measures)]
                    measure = Measure(track, header)
                    track.measures.append(measure)
        else:
            # Configure default track
            track = self.song.tracks[0]
            track.name = "Guitar"
            self._set_track_tuning(track, "standard")
        
        # Add measures (song already has 1)
        for _ in range(measures - 1):
            self._add_measure_header()
        
        # Add notes in batch
        if notes:
            self.add_notes_batch(notes)
        
        return self.get_info()
    
    def get_info(self) -> Dict[str, Any]:
        """Get song information."""
        if not self.song:
            return {"error": "No song loaded"}
        
        return {
            "title": self.song.title,
            "artist": self.song.artist,
            "album": self.song.album,
            "tempo": self.song.tempo,
            "tracks": len(self.song.tracks),
            "measures": len(self.song.measureHeaders),
            "track_details": [
                {
                    "index": i,
                    "name": t.name,
                    "strings": len(t.strings),
                    "tuning": self._get_tuning_name(t),
                    "instrument": t.channel.instrument
                }
                for i, t in enumerate(self.song.tracks)
            ]
        }
    
    def set_properties(self, title: str = None, artist: str = None,
                       album: str = None, tempo: int = None) -> bool:
        """Update song properties."""
        if not self.song:
            return False
        if title: self.song.title = title
        if artist: self.song.artist = artist
        if album: self.song.album = album
        if tempo: self.song.tempo = tempo
        return True
    
    # -------------------------------------------------------------------------
    # TRACK OPERATIONS
    # -------------------------------------------------------------------------
    
    def add_track(self, name: str, tuning: str = "standard", 
                  instrument: int = 25) -> int:
        """Add a new track. Returns track index."""
        if not self.song:
            self.create()
        
        track = Track(self.song)
        track.name = name
        track.channel.instrument = instrument
        self._set_track_tuning(track, tuning)
        
        # Create measures to match existing headers
        for header in self.song.measureHeaders:
            measure = Measure(track, header)
            track.measures.append(measure)
        
        self.song.tracks.append(track)
        return len(self.song.tracks) - 1
    
    def set_track_tuning(self, track_index: int, tuning: str) -> bool:
        """Change tuning of existing track."""
        if not self.song or track_index >= len(self.song.tracks):
            return False
        self._set_track_tuning(self.song.tracks[track_index], tuning)
        return True
    
    def get_tracks(self) -> List[Dict]:
        """Get all tracks info."""
        if not self.song:
            return []
        return [
            {
                "index": i,
                "name": t.name,
                "strings": len(t.strings),
                "tuning": self._get_tuning_name(t),
                "instrument": t.channel.instrument,
                "is_percussion": t.isPercussionTrack
            }
            for i, t in enumerate(self.song.tracks)
        ]
    
    # -------------------------------------------------------------------------
    # MEASURE OPERATIONS  
    # -------------------------------------------------------------------------
    
    def add_measures(self, count: int = 1) -> int:
        """Add multiple measures at once. Returns new measure count."""
        if not self.song:
            self.create()
        for _ in range(count):
            self._add_measure_header()
        return len(self.song.measureHeaders)
    
    def set_time_signature(self, measure: int, numerator: int, 
                           denominator: int) -> bool:
        """Set time signature for a measure."""
        if not self.song or measure >= len(self.song.measureHeaders):
            return False
        header = self.song.measureHeaders[measure]
        header.timeSignature.numerator = numerator
        header.timeSignature.denominator.value = denominator
        return True
    
    # -------------------------------------------------------------------------
    # NOTE OPERATIONS - SINGLE
    # -------------------------------------------------------------------------
    
    def add_note(self, track: int, measure: int, beat: int, 
                 string: int, fret: int, duration: int = 4) -> bool:
        """Add a single note."""
        return self.add_notes_batch([{
            "track": track, "measure": measure, "beat": beat,
            "string": string, "fret": fret, "duration": duration
        }])
    
    # -------------------------------------------------------------------------
    # NOTE OPERATIONS - BATCH (FAST!)
    # -------------------------------------------------------------------------
    
    def add_notes_batch(self, notes: List[Dict]) -> bool:
        """
        Add multiple notes in ONE operation.
        
        Each note dict can have:
            track: int (default 0)
            measure: int (default 0)
            beat: int (default 0)
            string: int (required, 1-6)
            fret: int (required, 0-24)
            duration: int (default 4 = quarter note)
            voice: int (default 0)
            palm_mute, hammer_on, pull_off, slide, bend, vibrato, ghost, dead: bool
        
        Returns True if all notes added successfully.
        """
        if not self.song:
            self.create()
        
        # Group notes by (track, measure, voice, beat) for efficiency
        grouped: Dict[Tuple, List[Dict]] = {}
        for n in notes:
            key = (
                n.get("track", 0),
                n.get("measure", 0),
                n.get("voice", 0),
                n.get("beat", 0)
            )
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(n)
        
        # Process each group
        for (track_idx, measure_idx, voice_idx, beat_idx), note_list in grouped.items():
            # Validate track
            if track_idx >= len(self.song.tracks):
                logger.warning(f"Invalid track {track_idx}")
                continue
            track = self.song.tracks[track_idx]
            
            # Ensure enough measures exist
            while measure_idx >= len(track.measures):
                self._add_measure_header()
            
            measure = track.measures[measure_idx]
            
            # Ensure voice exists
            while voice_idx >= len(measure.voices):
                measure.voices.append(Voice(measure))
            voice = measure.voices[voice_idx]
            
            # Ensure beat exists
            while beat_idx >= len(voice.beats):
                new_beat = Beat(voice)
                new_beat.duration = Duration()
                new_beat.duration.value = note_list[0].get("duration", 4)
                voice.beats.append(new_beat)
            beat = voice.beats[beat_idx]
            
            # Add all notes to this beat
            for n in note_list:
                note = Note(beat)
                note.string = n["string"]
                note.value = n["fret"]
                
                # Apply effects
                if n.get("palm_mute"): 
                    note.effect.palmMute = True
                if n.get("hammer_on"): 
                    note.effect.hammer = True
                if n.get("pull_off"): 
                    note.effect.hammer = True  # GP uses same flag
                if n.get("slide"): 
                    note.effect.slides = [1]  # SlideType.intoFromAbove
                if n.get("vibrato"): 
                    note.effect.vibrato = True
                if n.get("ghost"): 
                    note.effect.ghostNote = True
                if n.get("dead"): 
                    note.type = 3  # Dead note type
                
                beat.notes.append(note)
        
        return True
    
    # -------------------------------------------------------------------------
    # CHORD HELPERS
    # -------------------------------------------------------------------------
    
    def add_power_chord(self, track: int, measure: int, beat: int,
                        root_string: int, root_fret: int, 
                        duration: int = 4) -> bool:
        """
        Add a power chord (root + fifth + octave).
        
        Args:
            root_string: String for root note (typically 5 or 6)
            root_fret: Fret for root note
        """
        notes = [
            {"track": track, "measure": measure, "beat": beat,
             "string": root_string, "fret": root_fret, "duration": duration},
            {"track": track, "measure": measure, "beat": beat,
             "string": root_string - 1, "fret": root_fret + 2, "duration": duration},
            {"track": track, "measure": measure, "beat": beat,
             "string": root_string - 2, "fret": root_fret + 2, "duration": duration},
        ]
        return self.add_notes_batch(notes)
    
    def add_chord(self, track: int, measure: int, beat: int,
                  frets: List[int], duration: int = 4) -> bool:
        """
        Add a chord from fret positions.
        
        Args:
            frets: List of fret positions, low to high string.
                   Use -1 for muted strings.
                   e.g. E major = [0, 2, 2, 1, 0, 0]
        """
        notes = []
        for string_idx, fret in enumerate(frets):
            if fret >= 0:  # Skip muted strings (-1)
                notes.append({
                    "track": track, "measure": measure, "beat": beat,
                    "string": 6 - string_idx,  # Convert to GP string numbering
                    "fret": fret, "duration": duration
                })
        return self.add_notes_batch(notes)
    
    def add_palm_muted_notes(self, track: int, measure: int, 
                             string: int, frets: List[int],
                             start_beat: int = 0, duration: int = 8) -> bool:
        """Add a sequence of palm-muted notes (common in metal)."""
        notes = []
        for i, fret in enumerate(frets):
            notes.append({
                "track": track, "measure": measure, "beat": start_beat + i,
                "string": string, "fret": fret, "duration": duration,
                "palm_mute": True
            })
        return self.add_notes_batch(notes)
    
    # -------------------------------------------------------------------------
    # TAB IMPORT/EXPORT
    # -------------------------------------------------------------------------
    
    def import_tab(self, tab_string: str, track: int = 0, 
                   start_measure: int = 0, duration: int = 8) -> bool:
        """
        Import ASCII tab notation.
        
        Supports compact format:
            "6:0-0-0-0 4:2-3-2"
            (string:fret-fret-fret)
        """
        notes = self._parse_compact_tab(tab_string, track, start_measure, duration)
        return self.add_notes_batch(notes)
    
    def get_tab(self, track_index: int, start_measure: int = 0, 
                end_measure: int = None) -> str:
        """Generate ASCII tab for a track."""
        if not self.song or track_index >= len(self.song.tracks):
            return "Invalid track"
        
        track = self.song.tracks[track_index]
        num_strings = len(track.strings)
        
        if end_measure is None:
            end_measure = len(track.measures)
        
        # Initialize tab lines
        string_names = [self._note_name(s.value) for s in sorted(track.strings, key=lambda s: s.number)]
        tab_lines = [f"{name}|" for name in string_names]
        
        for m_idx in range(start_measure, min(end_measure, len(track.measures))):
            measure = track.measures[m_idx]
            
            # Collect notes per beat
            beat_data = []
            for voice in measure.voices:
                for beat in voice.beats:
                    beat_notes = {note.string: note.value for note in beat.notes}
                    beat_data.append(beat_notes)
            
            if not beat_data:
                beat_data = [{}]  # Empty measure
            
            # Render each beat
            for notes_dict in beat_data:
                for string_num in range(1, num_strings + 1):
                    line_idx = num_strings - string_num
                    if string_num in notes_dict:
                        fret = str(notes_dict[string_num])
                        tab_lines[line_idx] += fret.ljust(3, '-')
                    else:
                        tab_lines[line_idx] += "---"
            
            # Measure bar
            for i in range(num_strings):
                tab_lines[i] += "|"
        
        return '\n'.join(tab_lines)
    
    # -------------------------------------------------------------------------
    # TRACK ANALYSIS
    # -------------------------------------------------------------------------
    
    def get_track_notes(self, track_index: int) -> List[Dict]:
        """Get all notes from a track."""
        if not self.song or track_index >= len(self.song.tracks):
            return []
        
        track = self.song.tracks[track_index]
        notes = []
        
        for m_idx, measure in enumerate(track.measures):
            for v_idx, voice in enumerate(measure.voices):
                for b_idx, beat in enumerate(voice.beats):
                    for note in beat.notes:
                        notes.append({
                            "measure": m_idx,
                            "beat": b_idx,
                            "voice": v_idx,
                            "string": note.string,
                            "fret": note.value,
                            "duration": beat.duration.value
                        })
        
        return notes
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get song statistics."""
        if not self.song:
            return {}
        
        total_notes = 0
        track_stats = []
        
        for i, track in enumerate(self.song.tracks):
            track_notes = sum(
                len(beat.notes)
                for measure in track.measures
                for voice in measure.voices
                for beat in voice.beats
            )
            total_notes += track_notes
            track_stats.append({
                "name": track.name,
                "notes": track_notes,
                "measures": len(track.measures)
            })
        
        return {
            "title": self.song.title,
            "total_notes": total_notes,
            "tracks": track_stats,
            "measures": len(self.song.measureHeaders),
            "tempo": self.song.tempo
        }
    
    # -------------------------------------------------------------------------
    # INTERNAL HELPERS
    # -------------------------------------------------------------------------
    
    def _set_track_tuning(self, track: Track, tuning: str):
        """Set track tuning from preset name."""
        if tuning not in TUNINGS:
            tuning = "standard"
        
        midi_values = TUNINGS[tuning]
        track.strings = []
        
        for i, value in enumerate(reversed(midi_values)):  # GP: high to low
            gs = GuitarString(number=i + 1, value=value)
            track.strings.append(gs)
    
    def _get_tuning_name(self, track: Track) -> str:
        """Detect tuning name from track strings."""
        if not track.strings:
            return "unknown"
        
        values = [s.value for s in sorted(track.strings, key=lambda s: -s.number)]
        
        for name, preset_values in TUNINGS.items():
            if values == preset_values:
                return name
        
        return "custom"
    
    def _add_measure_header(self) -> int:
        """Add a measure header and corresponding measures to all tracks."""
        header = MeasureHeader()
        header.timeSignature = TimeSignature()
        header.timeSignature.numerator = 4
        header.timeSignature.denominator.value = 4
        self.song.measureHeaders.append(header)
        
        for track in self.song.tracks:
            measure = Measure(track, header)
            track.measures.append(measure)
        
        return len(self.song.measureHeaders) - 1
    
    def _note_name(self, midi_value: int) -> str:
        """Convert MIDI note to name."""
        return NOTE_NAMES[midi_value % 12]
    
    def _parse_compact_tab(self, tab: str, track: int, 
                          start_measure: int, duration: int) -> List[Dict]:
        """
        Parse compact tab format.
        Format: "6:0-3-5 5:2-4" means string 6 frets 0,3,5 then string 5 frets 2,4
        """
        notes = []
        beat = 0
        
        parts = tab.strip().split()
        for part in parts:
            if ':' in part:
                string_str, frets_str = part.split(':')
                string = int(string_str)
                frets = [int(f) for f in frets_str.split('-') if f.isdigit()]
                
                for fret in frets:
                    notes.append({
                        "track": track,
                        "measure": start_measure + (beat // 8),
                        "beat": beat % 8,
                        "string": string,
                        "fret": fret,
                        "duration": duration
                    })
                    beat += 1
        
        return notes


# Singleton instance
_controller: Optional[GuitarProController] = None

def get_controller() -> GuitarProController:
    """Get or create controller instance."""
    global _controller
    if _controller is None:
        _controller = GuitarProController()
    return _controller
