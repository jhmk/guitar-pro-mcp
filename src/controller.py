"""
Guitar Pro Controller v3.0
- Batch operations for speed
- TAB bulk import
- Pattern copy/repeat
- Copy from existing file
- Chord shortcuts
- Riff templates
- Multi-track batch add
- Transpose function
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple

import guitarpro as gp
from guitarpro import parse, write
from guitarpro.models import (
    Song, Track, Measure, MeasureHeader, Voice, Beat, Note,
    Duration, TimeSignature, KeySignature, GuitarString
)

logger = logging.getLogger(__name__)

# =============================================================================
# TUNING PRESETS (MIDI note numbers, low to high string)
# =============================================================================

TUNINGS = {
    # 6-string standard tunings
    "standard":     [40, 45, 50, 55, 59, 64],  # E2 A2 D3 G3 B3 E4
    "drop_d":       [38, 45, 50, 55, 59, 64],  # D2 A2 D3 G3 B3 E4
    "drop_c":       [36, 43, 48, 53, 57, 62],  # C2 G2 C3 F3 A3 D4
    "drop_b":       [35, 42, 47, 52, 56, 61],  # B1 F#2 B2 E3 G#3 C#4
    "drop_a":       [33, 40, 45, 50, 54, 59],  # A1 E2 A2 D3 F#3 B3
    "d_standard":   [38, 43, 48, 53, 57, 62],  # D2 G2 C3 F3 A3 D4
    "c_standard":   [36, 41, 46, 51, 55, 60],  # C2 F2 Bb2 Eb3 G3 C4
    "b_standard":   [35, 40, 45, 50, 54, 59],  # B1 E2 A2 D3 F#3 B3
    # Open tunings
    "open_d":       [38, 45, 50, 54, 57, 62],  # D2 A2 D3 F#3 A3 D4
    "open_g":       [38, 43, 50, 55, 59, 62],  # D2 G2 D3 G3 B3 D4
    "open_c":       [36, 43, 48, 55, 60, 64],  # C2 G2 C3 G3 C4 E4
    "dadgad":       [38, 45, 50, 55, 57, 62],  # D2 A2 D3 G3 A3 D4
    # 7-string
    "standard_7":   [35, 40, 45, 50, 55, 59, 64],  # B1 E2 A2 D3 G3 B3 E4
    "drop_a_7":     [33, 40, 45, 50, 55, 59, 64],  # A1 E2 A2 D3 G3 B3 E4
    # 8-string
    "standard_8":   [30, 35, 40, 45, 50, 55, 59, 64],  # F#1 B1 E2 A2 D3 G3 B3 E4
    "drop_e_8":     [28, 35, 40, 45, 50, 55, 59, 64],  # E1 B1 E2 A2 D3 G3 B3 E4
    # Bass
    "bass_standard": [28, 33, 38, 43],         # E1 A1 D2 G2
    "bass_drop_d":   [26, 33, 38, 43],         # D1 A1 D2 G2
    "bass_drop_c":   [24, 31, 36, 41],         # C1 G1 C2 F2
    "bass_5_standard": [23, 28, 33, 38, 43],   # B0 E1 A1 D2 G2
}

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Reverse lookup: tuple of MIDI values -> tuning name (O(1) instead of linear scan)
_TUNING_REVERSE = {tuple(v): k for k, v in TUNINGS.items()}

# =============================================================================
# CHORD LIBRARY
# =============================================================================

CHORDS = {
    # Major chords
    "E":    [0, 2, 2, 1, 0, 0],
    "F":    [1, 3, 3, 2, 1, 1],
    "G":    [3, 2, 0, 0, 0, 3],
    "A":    [-1, 0, 2, 2, 2, 0],
    "B":    [-1, 2, 4, 4, 4, 2],
    "C":    [-1, 3, 2, 0, 1, 0],
    "D":    [-1, -1, 0, 2, 3, 2],
    # Minor chords
    "Em":   [0, 2, 2, 0, 0, 0],
    "Fm":   [1, 3, 3, 1, 1, 1],
    "Gm":   [3, 5, 5, 3, 3, 3],
    "Am":   [-1, 0, 2, 2, 1, 0],
    "Bm":   [-1, 2, 4, 4, 3, 2],
    "Cm":   [-1, 3, 5, 5, 4, 3],
    "Dm":   [-1, -1, 0, 2, 3, 1],
    # Power chords
    "E5":   [0, 2, 2, -1, -1, -1],
    "F5":   [1, 3, 3, -1, -1, -1],
    "G5":   [3, 5, 5, -1, -1, -1],
    "A5":   [-1, 0, 2, 2, -1, -1],
    "B5":   [-1, 2, 4, 4, -1, -1],
    "C5":   [-1, 3, 5, 5, -1, -1],
    "D5":   [-1, -1, 0, 2, 3, -1],
    # 7th chords
    "E7":   [0, 2, 0, 1, 0, 0],
    "A7":   [-1, 0, 2, 0, 2, 0],
    "D7":   [-1, -1, 0, 2, 1, 2],
    "G7":   [3, 2, 0, 0, 0, 1],
    "B7":   [-1, 2, 1, 2, 0, 2],
    # Minor 7th
    "Em7":  [0, 2, 0, 0, 0, 0],
    "Am7":  [-1, 0, 2, 0, 1, 0],
    "Dm7":  [-1, -1, 0, 2, 1, 1],
    # Sus chords
    "Asus2": [-1, 0, 2, 2, 0, 0],
    "Asus4": [-1, 0, 2, 2, 3, 0],
    "Dsus2": [-1, -1, 0, 2, 3, 0],
    "Dsus4": [-1, -1, 0, 2, 3, 3],
}

# =============================================================================
# RIFF TEMPLATES
# =============================================================================

RIFF_TEMPLATES = {
    "chug_basic": {
        "description": "Basic palm mute chug (8 eighth notes)",
        "duration": 8,
        "pattern": [
            {"beat": 0, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 1, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 2, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 3, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 4, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 5, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 6, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 7, "string": 6, "fret": 0, "palm_mute": True},
        ]
    },
    "chug_gallop": {
        "description": "Galloping rhythm (Iron Maiden style)",
        "duration": 8,
        "pattern": [
            {"beat": 0, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 2, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 3, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 4, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 6, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 7, "string": 6, "fret": 0, "palm_mute": True},
        ]
    },
    "chug_breakdown": {
        "description": "Breakdown pattern with open accents",
        "duration": 8,
        "pattern": [
            {"beat": 0, "string": 6, "fret": 0},
            {"beat": 1, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 2, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 3, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 4, "string": 6, "fret": 0},
            {"beat": 5, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 6, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 7, "string": 6, "fret": 0, "palm_mute": True},
        ]
    },
    "power_quarters": {
        "description": "Quarter note power chords",
        "duration": 4,
        "pattern": [
            {"beat": 0, "string": 6, "fret": 0},
            {"beat": 0, "string": 5, "fret": 2},
            {"beat": 0, "string": 4, "fret": 2},
            {"beat": 1, "string": 6, "fret": 0},
            {"beat": 1, "string": 5, "fret": 2},
            {"beat": 1, "string": 4, "fret": 2},
            {"beat": 2, "string": 6, "fret": 0},
            {"beat": 2, "string": 5, "fret": 2},
            {"beat": 2, "string": 4, "fret": 2},
            {"beat": 3, "string": 6, "fret": 0},
            {"beat": 3, "string": 5, "fret": 2},
            {"beat": 3, "string": 4, "fret": 2},
        ]
    },
    "djent_basic": {
        "description": "Basic djent syncopation",
        "duration": 8,
        "pattern": [
            {"beat": 0, "string": 6, "fret": 0},
            {"beat": 0, "string": 5, "fret": 2},
            {"beat": 3, "string": 6, "fret": 0, "palm_mute": True},
            {"beat": 5, "string": 6, "fret": 0},
            {"beat": 5, "string": 5, "fret": 2},
            {"beat": 7, "string": 6, "fret": 0, "palm_mute": True},
        ]
    },
    "thrash_pick": {
        "description": "Thrash metal alternate picking",
        "duration": 16,
        "pattern": [
            {"beat": i, "string": 6, "fret": 0, "palm_mute": True}
            for i in range(16)
        ]
    },
}


# =============================================================================
# MAIN CONTROLLER
# =============================================================================

class GuitarProController:
    """Guitar Pro Controller v3.0 with advanced features."""
    
    def __init__(self):
        self.song: Optional[Song] = None
        self._clipboard: List[Dict] = []
        
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
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
    
    # =========================================================================
    # SONG OPERATIONS
    # =========================================================================
    
    def create(self, title: str = "New Song", artist: str = "", 
               tempo: int = 120, tuning: str = "standard") -> Dict[str, Any]:
        """Create a new song with sensible defaults."""
        self.song = Song()
        self.song.title = title
        self.song.artist = artist
        self.song.tempo = tempo
        
        if self.song.tracks:
            track = self.song.tracks[0]
            track.name = "Guitar"
            track.channel.instrument = 25
            self._set_track_tuning(track, tuning)
        
        return self.get_info()
    
    def create_complete(self, title: str, artist: str = "", tempo: int = 120,
                        tracks: List[Dict] = None, measures: int = 4,
                        notes: List[Dict] = None) -> Dict[str, Any]:
        """Create a complete song in ONE call."""
        self.song = Song()
        self.song.title = title
        self.song.artist = artist
        self.song.tempo = tempo
        
        if tracks:
            for i, t in enumerate(tracks):
                if i == 0:
                    track = self.song.tracks[0]
                else:
                    track = Track(self.song)
                    self.song.tracks.append(track)
                track.name = t.get("name", f"Track {i+1}")
                track.channel.instrument = t.get("instrument", 25)
                self._set_track_tuning(track, t.get("tuning", "standard"))
                while len(track.measures) < len(self.song.measureHeaders):
                    header = self.song.measureHeaders[len(track.measures)]
                    measure = Measure(track, header)
                    track.measures.append(measure)
        else:
            track = self.song.tracks[0]
            track.name = "Guitar"
            self._set_track_tuning(track, "standard")
        
        for _ in range(measures - 1):
            self._add_measure_header()
        
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
        if title is not None: self.song.title = title
        if artist is not None: self.song.artist = artist
        if album is not None: self.song.album = album
        if tempo is not None: self.song.tempo = tempo
        return True
    
    # =========================================================================
    # TRACK OPERATIONS
    # =========================================================================
    
    def add_track(self, name: str, tuning: str = "standard", 
                  instrument: int = 25) -> int:
        """Add a new track. Returns track index."""
        if not self.song:
            self.create()
        
        track = Track(self.song)
        track.name = name
        track.channel.instrument = instrument
        self._set_track_tuning(track, tuning)
        
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
    
    # =========================================================================
    # MEASURE OPERATIONS  
    # =========================================================================
    
    def add_measures(self, count: int = 1) -> int:
        """Add multiple measures. Returns new measure count."""
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
    
    # =========================================================================
    # NOTE OPERATIONS - BATCH (CORE!)
    # =========================================================================
    
    def add_note(self, track: int, measure: int, beat: int, 
                 string: int, fret: int, duration: int = 4) -> bool:
        """Add a single note."""
        return self.add_notes_batch([{
            "track": track, "measure": measure, "beat": beat,
            "string": string, "fret": fret, "duration": duration
        }])
    
    def add_notes_batch(self, notes: List[Dict]) -> bool:
        """
        Add multiple notes in ONE operation. 
        IMPORTANT: Beat must be integer (0, 1, 2...), not float!
        """
        if not self.song:
            self.create()
        
        grouped: Dict[Tuple, List[Dict]] = {}
        for n in notes:
            beat_val = int(n.get("beat", 0))  # Force integer
            key = (
                n.get("track", 0),
                n.get("measure", 0),
                n.get("voice", 0),
                beat_val
            )
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(n)
        
        for (track_idx, measure_idx, voice_idx, beat_idx), note_list in grouped.items():
            if track_idx >= len(self.song.tracks):
                continue
            track = self.song.tracks[track_idx]
            
            while measure_idx >= len(track.measures):
                self._add_measure_header()
            
            measure = track.measures[measure_idx]
            
            while voice_idx >= len(measure.voices):
                measure.voices.append(Voice(measure))
            voice = measure.voices[voice_idx]
            
            while beat_idx >= len(voice.beats):
                new_beat = Beat(voice)
                new_beat.duration = Duration()
                new_beat.duration.value = note_list[0].get("duration", 4)
                voice.beats.append(new_beat)
            beat = voice.beats[beat_idx]
            
            for n in note_list:
                note = Note(beat)
                note.string = n["string"]
                note.value = n["fret"]
                
                if n.get("palm_mute"): 
                    note.effect.palmMute = True
                if n.get("hammer_on") or n.get("pull_off"): 
                    note.effect.hammer = True
                if n.get("slide"): 
                    note.effect.slides = [1]
                if n.get("vibrato"): 
                    note.effect.vibrato = True
                if n.get("ghost"): 
                    note.effect.ghostNote = True
                if n.get("dead"): 
                    note.type = 3
                if n.get("let_ring"):
                    note.effect.letRing = True
                
                beat.notes.append(note)
        
        return True
    
    # =========================================================================
    # TAB BULK IMPORT (IMPORTANT!)
    # =========================================================================
    
    def import_tab_bulk(self, tab: str, track: int = 0, 
                        start_measure: int = 0, duration: int = 8) -> Dict[str, Any]:
        """
        Import complete ASCII tablature.
        
        Standard format:
            e|--0--3--5--3--0--|
            B|-----------------|
            G|-----------------|
            D|-----------------|
            A|-----------------|
            E|-----------------|
        
        Compact format:
            "6:0-0-3-5 5:2-2-0"
        """
        if not self.song:
            self.create()
        
        tab = tab.strip()
        
        if '|' in tab and any(c in tab.lower() for c in 'ebgdae'):
            notes = self._parse_standard_tab(tab, track, start_measure, duration)
        else:
            notes = self._parse_compact_tab(tab, track, start_measure, duration)
        
        self.add_notes_batch(notes)
        return {"notes_added": len(notes), "measures_used": self._count_measures(notes)}
    
    def _parse_standard_tab(self, tab: str, track: int, 
                           start_measure: int, duration: int) -> List[Dict]:
        """Parse standard ASCII tab format with proper measure handling."""
        notes = []
        lines = tab.strip().split('\n')
        
        # Build tab lines list
        tab_lines = []
        for line in lines:
            line = line.strip()
            # Match e|, E|, B|, etc.
            match = re.match(r'^([eEbBgGdDaA])\s*\|(.*)$', line)
            if match:
                string_char = match.group(1).upper()
                content = match.group(2)
                
                string_map = {'B': 2, 'G': 3, 'D': 4, 'A': 5}
                if string_char == 'E':
                    string_num = 1 if len(tab_lines) == 0 else 6
                else:
                    string_num = string_map.get(string_char, 1)
                
                tab_lines.append((string_num, content))
        
        if not tab_lines:
            return notes
        
        # Process content - find all columns with frets
        max_len = max(len(content) for _, content in tab_lines)
        
        current_measure = start_measure
        current_beat = 0
        beats_per_measure = 8 if duration == 8 else 4
        
        col = 0
        while col < max_len:
            # Check for measure bar
            is_bar = all(
                col < len(content) and content[col] == '|'
                for _, content in tab_lines
            )
            if is_bar:
                col += 1
                continue
            
            # Collect notes at this column
            column_notes = []
            max_fret_len = 1
            
            for string_num, content in tab_lines:
                if col >= len(content):
                    continue
                    
                char = content[col]
                if char.isdigit():
                    fret_str = char
                    if col + 1 < len(content) and content[col + 1].isdigit():
                        fret_str += content[col + 1]
                        max_fret_len = 2
                    
                    column_notes.append({
                        "track": track,
                        "measure": current_measure,
                        "beat": current_beat,
                        "string": string_num,
                        "fret": int(fret_str),
                        "duration": duration
                    })
            
            if column_notes:
                notes.extend(column_notes)
                current_beat += 1
                if current_beat >= beats_per_measure:
                    current_beat = 0
                    current_measure += 1
            
            col += max_fret_len
            
            # Skip dashes
            while col < max_len:
                has_content = any(
                    col < len(content) and (content[col].isdigit() or content[col] == '|')
                    for _, content in tab_lines
                )
                if has_content:
                    break
                col += 1
        
        return notes
    
    def _parse_compact_tab(self, tab: str, track: int, 
                          start_measure: int, duration: int) -> List[Dict]:
        """Parse compact format: '6:0-3-5 5:2-4'"""
        notes = []
        current_beat = 0
        beats_per_measure = 8 if duration == 8 else 4
        current_measure = start_measure
        
        parts = tab.strip().split()
        for part in parts:
            if ':' in part:
                string_str, frets_str = part.split(':', 1)
                string = int(string_str)
                frets = frets_str.split('-')
                
                for fret_str in frets:
                    fret_str = fret_str.strip()
                    if fret_str.lstrip('-').isdigit() or fret_str == '0':
                        fret = int(fret_str)
                        notes.append({
                            "track": track,
                            "measure": current_measure,
                            "beat": current_beat,
                            "string": string,
                            "fret": fret,
                            "duration": duration
                        })
                        current_beat += 1
                        if current_beat >= beats_per_measure:
                            current_beat = 0
                            current_measure += 1
        
        return notes
    
    def _count_measures(self, notes: List[Dict]) -> int:
        if not notes:
            return 0
        return max(n.get("measure", 0) for n in notes) + 1
    
    # =========================================================================
    # PATTERN COPY/REPEAT
    # =========================================================================
    
    def copy_measures(self, track_index: int, start_measure: int, 
                      end_measure: int) -> Dict[str, Any]:
        """Copy measures to clipboard."""
        if not self.song or track_index >= len(self.song.tracks):
            return {"error": "Invalid track"}
        
        track = self.song.tracks[track_index]
        self._clipboard = []
        
        for m_idx in range(start_measure, min(end_measure + 1, len(track.measures))):
            measure = track.measures[m_idx]
            for voice in measure.voices:
                for b_idx, beat in enumerate(voice.beats):
                    for note in beat.notes:
                        note_data = {
                            "measure": m_idx - start_measure,
                            "beat": b_idx,
                            "string": note.string,
                            "fret": note.value,
                            "duration": beat.duration.value,
                        }
                        if note.effect and note.effect.palmMute:
                            note_data["palm_mute"] = True
                        if note.effect and note.effect.hammer:
                            note_data["hammer_on"] = True
                        self._clipboard.append(note_data)
        
        return {"notes_copied": len(self._clipboard), 
                "measures": end_measure - start_measure + 1}
    
    def paste_measures(self, track_index: int, start_measure: int, 
                       repeat: int = 1) -> Dict[str, Any]:
        """Paste clipboard, optionally repeating."""
        if not self._clipboard:
            return {"error": "Clipboard empty"}
        
        if not self.song:
            self.create()
        
        pattern_measures = max(n["measure"] for n in self._clipboard) + 1
        
        notes_to_add = []
        for rep in range(repeat):
            offset = rep * pattern_measures
            for note in self._clipboard:
                notes_to_add.append({
                    **note,
                    "track": track_index,
                    "measure": start_measure + note["measure"] + offset
                })
        
        total_needed = start_measure + (pattern_measures * repeat)
        while len(self.song.measureHeaders) < total_needed:
            self._add_measure_header()
        
        self.add_notes_batch(notes_to_add)
        return {"notes_added": len(notes_to_add), 
                "measures_filled": pattern_measures * repeat}
    
    def repeat_pattern(self, track_index: int, source_start: int, source_end: int,
                       dest_start: int, times: int = 1) -> Dict[str, Any]:
        """Copy and repeat a pattern in one call."""
        self.copy_measures(track_index, source_start, source_end)
        return self.paste_measures(track_index, dest_start, times)
    
    # =========================================================================
    # COPY FROM EXISTING FILE
    # =========================================================================
    
    def copy_track_from_file(self, source_path: str, source_track_index: int,
                             dest_track_name: str = None,
                             start_measure: int = 0, 
                             end_measure: int = None) -> Dict[str, Any]:
        """Copy a track from another Guitar Pro file."""
        if not self.song:
            self.create()
        
        source_song = parse(source_path)
        
        if source_track_index >= len(source_song.tracks):
            return {"error": f"Source track {source_track_index} not found"}
        
        source_track = source_song.tracks[source_track_index]
        
        if end_measure is None:
            end_measure = len(source_track.measures) - 1
        
        track_name = dest_track_name or source_track.name
        new_track = Track(self.song)
        new_track.name = track_name
        new_track.channel.instrument = source_track.channel.instrument
        
        # Copy tuning
        new_track.strings = []
        for s in source_track.strings:
            new_track.strings.append(GuitarString(number=s.number, value=s.value))
        
        measures_needed = end_measure - start_measure + 1
        while len(self.song.measureHeaders) < measures_needed:
            self._add_measure_header()
        
        # Collect notes
        notes_to_add = []
        for m_idx in range(start_measure, min(end_measure + 1, len(source_track.measures))):
            source_measure = source_track.measures[m_idx]
            dest_measure_idx = m_idx - start_measure
            
            for v_idx, voice in enumerate(source_measure.voices):
                for b_idx, beat in enumerate(voice.beats):
                    for note in beat.notes:
                        note_data = {
                            "track": len(self.song.tracks),
                            "measure": dest_measure_idx,
                            "beat": b_idx,
                            "voice": v_idx,
                            "string": note.string,
                            "fret": note.value,
                            "duration": beat.duration.value,
                        }
                        # Copy effects
                        if note.effect:
                            if note.effect.palmMute:
                                note_data["palm_mute"] = True
                            if note.effect.hammer:
                                note_data["hammer_on"] = True
                            if note.effect.vibrato:
                                note_data["vibrato"] = True
                        notes_to_add.append(note_data)
        
        # Create measures for new track
        for header in self.song.measureHeaders:
            measure = Measure(new_track, header)
            new_track.measures.append(measure)
        
        self.song.tracks.append(new_track)
        self.add_notes_batch(notes_to_add)
        
        return {
            "track_name": track_name,
            "track_index": len(self.song.tracks) - 1,
            "notes_copied": len(notes_to_add),
            "measures_copied": measures_needed
        }
    
    # =========================================================================
    # CHORD SHORTCUTS
    # =========================================================================
    
    def add_chord_by_name(self, track: int, measure: int, beat: int,
                          chord_name: str, duration: int = 4) -> bool:
        """Add a chord by name (E, Am, G5, etc.)."""
        if chord_name not in CHORDS:
            return False
        return self.add_chord(track, measure, beat, CHORDS[chord_name], duration)
    
    def add_chord(self, track: int, measure: int, beat: int,
                  frets: List[int], duration: int = 4) -> bool:
        """Add a chord from fret positions [low to high string]."""
        notes = []
        for string_idx, fret in enumerate(frets):
            if fret >= 0:
                notes.append({
                    "track": track, "measure": measure, "beat": beat,
                    "string": len(frets) - string_idx,
                    "fret": fret, "duration": duration
                })
        return self.add_notes_batch(notes)
    
    def add_power_chord(self, track: int, measure: int, beat: int,
                        root_string: int, root_fret: int, 
                        duration: int = 4) -> bool:
        """Add a power chord (root + fifth + octave)."""
        notes = [
            {"track": track, "measure": measure, "beat": beat,
             "string": root_string, "fret": root_fret, "duration": duration},
            {"track": track, "measure": measure, "beat": beat,
             "string": root_string - 1, "fret": root_fret + 2, "duration": duration},
            {"track": track, "measure": measure, "beat": beat,
             "string": root_string - 2, "fret": root_fret + 2, "duration": duration},
        ]
        return self.add_notes_batch(notes)
    
    def add_chord_progression(self, track: int, start_measure: int,
                              chords: List[str], beats_per_chord: int = 4,
                              duration: int = 4) -> Dict[str, Any]:
        """Add a chord progression (e.g., ["E", "A", "B", "E"])."""
        if not self.song:
            self.create()
        current_measure = start_measure
        current_beat = 0
        chords_added = 0
        
        for chord_name in chords:
            if chord_name in CHORDS:
                # Ensure measure exists
                while current_measure >= len(self.song.measureHeaders):
                    self._add_measure_header()
                    
                self.add_chord_by_name(track, current_measure, current_beat, 
                                       chord_name, duration)
                chords_added += 1
            
            current_beat += beats_per_chord
            while current_beat >= 4:
                current_beat -= 4
                current_measure += 1
        
        return {"chords_added": chords_added}
    
    def list_chords(self) -> List[str]:
        """List available chord names."""
        return list(CHORDS.keys())
    
    # =========================================================================
    # RIFF TEMPLATES
    # =========================================================================
    
    def list_riff_templates(self) -> Dict[str, str]:
        """List available riff templates."""
        return {name: t["description"] for name, t in RIFF_TEMPLATES.items()}
    
    def add_riff_template(self, track: int, measure: int, template_name: str,
                          root_fret: int = 0, repeat: int = 1) -> Dict[str, Any]:
        """Add a riff template, transposed to root_fret."""
        if template_name not in RIFF_TEMPLATES:
            return {"error": f"Unknown template: {template_name}"}
        
        if not self.song:
            self.create()

        template = RIFF_TEMPLATES[template_name]
        notes_to_add = []
        
        for rep in range(repeat):
            for note_template in template["pattern"]:
                notes_to_add.append({
                    "track": track,
                    "measure": measure + rep,
                    "beat": note_template["beat"],
                    "string": note_template["string"],
                    "fret": note_template["fret"] + root_fret,
                    "duration": template["duration"],
                    "palm_mute": note_template.get("palm_mute", False)
                })
        
        while len(self.song.measureHeaders) < measure + repeat:
            self._add_measure_header()
        
        self.add_notes_batch(notes_to_add)
        return {"notes_added": len(notes_to_add), "measures": repeat}
    
    # =========================================================================
    # MULTI-TRACK BATCH ADD
    # =========================================================================
    
    def add_notes_multi_track(self, notes_by_track: Dict[int, List[Dict]]) -> Dict[str, Any]:
        """
        Add notes to multiple tracks at once.
        
        Args:
            notes_by_track: {0: [notes...], 1: [notes...]}
        """
        all_notes = []
        for track_idx, notes in notes_by_track.items():
            for note in notes:
                all_notes.append({**note, "track": track_idx})
        
        self.add_notes_batch(all_notes)
        return {"total_notes_added": len(all_notes), "tracks_modified": len(notes_by_track)}
    
    # =========================================================================
    # TRANSPOSE
    # =========================================================================
    
    def transpose_track(self, track_index: int, semitones: int,
                        start_measure: int = 0, end_measure: int = None) -> Dict[str, Any]:
        """Transpose notes in a track by semitones."""
        if not self.song or track_index >= len(self.song.tracks):
            return {"error": "Invalid track"}
        
        track = self.song.tracks[track_index]
        if end_measure is None:
            end_measure = len(track.measures) - 1
        
        notes_transposed = 0
        
        for m_idx in range(start_measure, min(end_measure + 1, len(track.measures))):
            measure = track.measures[m_idx]
            for voice in measure.voices:
                for beat in voice.beats:
                    for note in beat.notes:
                        new_fret = note.value + semitones
                        if 0 <= new_fret <= 24:
                            note.value = new_fret
                            notes_transposed += 1
        
        return {"notes_transposed": notes_transposed}
    
    def transpose_section(self, track_index: int, start_measure: int, 
                          end_measure: int, semitones: int) -> Dict[str, Any]:
        """Transpose a specific section."""
        return self.transpose_track(track_index, semitones, start_measure, end_measure)
    
    # =========================================================================
    # PALM MUTES
    # =========================================================================
    
    def add_palm_muted_notes(self, track: int, measure: int, 
                             string: int, frets: List[int],
                             start_beat: int = 0, duration: int = 8) -> bool:
        """Add palm-muted notes sequence."""
        notes = []
        for i, fret in enumerate(frets):
            notes.append({
                "track": track, "measure": measure, "beat": start_beat + i,
                "string": string, "fret": fret, "duration": duration,
                "palm_mute": True
            })
        return self.add_notes_batch(notes)
    
    # =========================================================================
    # TAB EXPORT & STATS
    # =========================================================================
    
    def get_tab(self, track_index: int, start_measure: int = 0,
                end_measure: int = None) -> str:
        """Generate ASCII tab."""
        if not self.song or track_index >= len(self.song.tracks):
            return "Invalid track"

        track = self.song.tracks[track_index]
        num_strings = len(track.strings)

        if end_measure is None:
            end_measure = len(track.measures)

        string_names = [self._note_name(s.value) for s in sorted(track.strings, key=lambda s: s.number)]
        # Use list-of-lists for O(1) appends instead of string concatenation
        tab_parts = [[f"{name}|"] for name in string_names]

        for m_idx in range(start_measure, min(end_measure, len(track.measures))):
            measure = track.measures[m_idx]

            beat_data = []
            for voice in measure.voices:
                for beat in voice.beats:
                    beat_notes = {note.string: note.value for note in beat.notes}
                    beat_data.append(beat_notes)

            if not beat_data:
                beat_data = [{}]

            for notes_dict in beat_data:
                for string_num in range(1, num_strings + 1):
                    line_idx = string_num - 1
                    if string_num in notes_dict:
                        fret = str(notes_dict[string_num])
                        tab_parts[line_idx].append(fret.ljust(3, '-'))
                    else:
                        tab_parts[line_idx].append("---")

            for i in range(num_strings):
                tab_parts[i].append("|")

        return '\n'.join(''.join(parts) for parts in tab_parts)
    
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
    
    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================
    
    def _set_track_tuning(self, track: Track, tuning: str):
        """Set track tuning from preset name."""
        if tuning not in TUNINGS:
            tuning = "standard"
        
        midi_values = TUNINGS[tuning]
        track.strings = []
        
        for i, value in enumerate(reversed(midi_values)):
            gs = GuitarString(number=i + 1, value=value)
            track.strings.append(gs)
    
    def _get_tuning_name(self, track: Track) -> str:
        """Detect tuning name from track strings."""
        if not track.strings:
            return "unknown"

        values = tuple(s.value for s in sorted(track.strings, key=lambda s: -s.number))
        return _TUNING_REVERSE.get(values, "custom")
    
    def _add_measure_header(self) -> int:
        """Add a measure header and measures to all tracks."""
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


# Singleton instance
_controller: Optional[GuitarProController] = None

def get_controller() -> GuitarProController:
    """Get or create controller instance."""
    global _controller
    if _controller is None:
        _controller = GuitarProController()
    return _controller
