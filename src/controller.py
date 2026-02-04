"""
Guitar Pro Controller v3.0

FEATURES:
- Read/Write GP3/4/5
- Read GP7/8 (.gp)
- MusicXML Import/Export
- All note effects: bend, tremolo, trill, harmonics, grace notes, etc.
- Song structure: markers, repeats, tempo changes
- Batch operations, TAB import, chords, templates, transpose
"""

import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from enum import IntEnum

import guitarpro as gp
from guitarpro import parse, write
from guitarpro.models import (
    Song, Track, Measure, MeasureHeader, Voice, Beat, Note,
    Duration, TimeSignature, NoteEffect, GuitarString, BendEffect,
    BendType, BendPoint, GraceEffect, GraceEffectTransition, HarmonicEffect,
    NaturalHarmonic, ArtificialHarmonic, TappedHarmonic, PinchHarmonic,
    TrillEffect, TremoloPickingEffect, Marker, Velocities, SlapEffect,
    BeatEffect, BeatStroke, BeatStrokeDirection, MixTableChange,
    MixTableItem, Tuplet
)

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

TUNINGS = {
    "standard": [40, 45, 50, 55, 59, 64],
    "drop_d": [38, 45, 50, 55, 59, 64],
    "drop_c": [36, 43, 48, 53, 57, 62],
    "drop_b": [35, 42, 47, 52, 56, 61],
    "drop_a": [33, 40, 45, 50, 54, 59],
    "d_standard": [38, 43, 48, 53, 57, 62],
    "c_standard": [36, 41, 46, 51, 55, 60],
    "b_standard": [35, 40, 45, 50, 54, 59],
    "open_d": [38, 45, 50, 54, 57, 62],
    "open_g": [38, 43, 50, 55, 59, 62],
    "open_c": [36, 43, 48, 55, 60, 64],
    "dadgad": [38, 45, 50, 55, 57, 62],
    "standard_7": [35, 40, 45, 50, 55, 59, 64],
    "drop_a_7": [33, 40, 45, 50, 55, 59, 64],
    "standard_8": [30, 35, 40, 45, 50, 55, 59, 64],
    "drop_e_8": [28, 35, 40, 45, 50, 55, 59, 64],
    "bass_standard": [28, 33, 38, 43],
    "bass_drop_d": [26, 33, 38, 43],
    "bass_drop_c": [24, 31, 36, 41],
    "bass_5_standard": [23, 28, 33, 38, 43],
}

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

CHORDS = {
    "E": [0, 2, 2, 1, 0, 0], "F": [1, 3, 3, 2, 1, 1], "G": [3, 2, 0, 0, 0, 3],
    "A": [-1, 0, 2, 2, 2, 0], "B": [-1, 2, 4, 4, 4, 2], "C": [-1, 3, 2, 0, 1, 0],
    "D": [-1, -1, 0, 2, 3, 2],
    "Em": [0, 2, 2, 0, 0, 0], "Fm": [1, 3, 3, 1, 1, 1], "Gm": [3, 5, 5, 3, 3, 3],
    "Am": [-1, 0, 2, 2, 1, 0], "Bm": [-1, 2, 4, 4, 3, 2], "Cm": [-1, 3, 5, 5, 4, 3],
    "Dm": [-1, -1, 0, 2, 3, 1],
    "E5": [0, 2, 2, -1, -1, -1], "F5": [1, 3, 3, -1, -1, -1], "G5": [3, 5, 5, -1, -1, -1],
    "A5": [-1, 0, 2, 2, -1, -1], "B5": [-1, 2, 4, 4, -1, -1], "C5": [-1, 3, 5, 5, -1, -1],
    "D5": [-1, -1, 0, 2, 3, -1],
    "E7": [0, 2, 0, 1, 0, 0], "A7": [-1, 0, 2, 0, 2, 0], "D7": [-1, -1, 0, 2, 1, 2],
    "G7": [3, 2, 0, 0, 0, 1], "B7": [-1, 2, 1, 2, 0, 2],
    "Em7": [0, 2, 0, 0, 0, 0], "Am7": [-1, 0, 2, 0, 1, 0], "Dm7": [-1, -1, 0, 2, 1, 1],
    "Asus2": [-1, 0, 2, 2, 0, 0], "Asus4": [-1, 0, 2, 2, 3, 0],
    "Dsus2": [-1, -1, 0, 2, 3, 0], "Dsus4": [-1, -1, 0, 2, 3, 3],
}

RIFF_TEMPLATES = {
    "chug_basic": {
        "description": "Basic palm mute chug (8 eighth notes)",
        "duration": 8,
        "pattern": [{"beat": i, "string": 6, "fret": 0, "palm_mute": True} for i in range(8)]
    },
    "chug_gallop": {
        "description": "Galloping rhythm",
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
        "description": "Breakdown pattern",
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
            {"beat": b, "string": s, "fret": 0 if s == 6 else 2}
            for b in range(4) for s in [6, 5, 4]
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
        "pattern": [{"beat": i, "string": 6, "fret": 0, "palm_mute": True} for i in range(16)]
    },
}

# Bend constants (in quarter tones, 100 = 1 semitone)
BEND_QUARTER = 25
BEND_HALF = 50
BEND_FULL = 100
BEND_FULL_HALF = 150
BEND_DOUBLE = 200


# =============================================================================
# GP7/8 READER
# =============================================================================

class GP8Reader:
    """Reads Guitar Pro 7/8 (.gp) files."""
    
    def __init__(self):
        self.gpif_root = None
        self.version = None
        self._notes = {}
        self._beats = {}
        self._voices = {}
        self._bars = {}
        self._rhythms = {}
        
    def read(self, path: str) -> Dict[str, Any]:
        with zipfile.ZipFile(path, 'r') as z:
            if 'VERSION' in z.namelist():
                self.version = z.read('VERSION').decode('utf-8').strip()
            gpif_path = 'Content/score.gpif'
            if gpif_path not in z.namelist():
                raise ValueError("Invalid GP7/8 file")
            self.gpif_root = ET.fromstring(z.read(gpif_path))
        return self._parse_gpif()
    
    def _parse_gpif(self) -> Dict[str, Any]:
        root = self.gpif_root
        result = {"format_version": self.version, "title": "", "artist": "", "album": "",
                  "tempo": 120, "tracks": [], "master_bars": []}
        
        score = root.find("Score")
        if score is not None:
            result["title"] = self._text(score, "Title") or ""
            result["artist"] = self._text(score, "Artist") or ""
        
        mt = root.find("MasterTrack")
        if mt is not None:
            autos = mt.find("Automations")
            if autos is not None:
                for a in autos.findall("Automation"):
                    if self._text(a, "Type") == "Tempo":
                        v = self._text(a, "Value")
                        if v: result["tempo"] = int(float(v.split()[0]))
                        break
        
        self._build_lookups(root)
        
        tracks = root.find("Tracks")
        if tracks is not None:
            for t in tracks.findall("Track"):
                result["tracks"].append(self._parse_track(t))
        
        mbs = root.find("MasterBars")
        if mbs is not None:
            for mb in mbs.findall("MasterBar"):
                result["master_bars"].append(self._parse_master_bar(mb))
        
        for mb_idx, mb in enumerate(result["master_bars"]):
            for ti, bar_id in enumerate(mb["bar_ids"]):
                if ti < len(result["tracks"]) and bar_id in self._bars:
                    result["tracks"][ti].setdefault("bars", []).append({
                        "measure": mb_idx, "voices": self._bars[bar_id]["voices"]
                    })
        return result
    
    def _build_lookups(self, root):
        for r in (root.find("Rhythms") or []):
            self._rhythms[r.get("id")] = self._parse_rhythm(r)
        for n in (root.find("Notes") or []):
            self._notes[n.get("id")] = self._parse_note(n)
        for b in (root.find("Beats") or []):
            self._beats[b.get("id")] = self._parse_beat(b)
        for v in (root.find("Voices") or []):
            self._voices[v.get("id")] = self._parse_voice(v)
        for b in (root.find("Bars") or []):
            self._bars[b.get("id")] = self._parse_bar(b)
    
    def _parse_rhythm(self, e) -> Dict:
        dm = {"Whole": 1, "Half": 2, "Quarter": 4, "Eighth": 8, "16th": 16, "32nd": 32}
        nv = e.find("NoteValue")
        return {"duration": dm.get(nv.text if nv is not None else "Quarter", 4)}
    
    def _parse_note(self, e) -> Dict:
        d = {"fret": 0, "string": 1, "palm_mute": False, "hammer_on": False,
             "vibrato": False, "slide": False, "dead": False, "ghost": False,
             "let_ring": False, "bend": None, "harmonic": None, "trill": None}
        props = e.find("Properties")
        if props:
            for p in props.findall("Property"):
                n = p.get("name")
                if n == "Fret":
                    f = p.find("Fret")
                    if f is not None and f.text: d["fret"] = int(f.text)
                elif n == "String":
                    s = p.find("String")
                    if s is not None and s.text: d["string"] = int(s.text) + 1
                elif n == "PalmMuted": d["palm_mute"] = p.find("Enable") is not None
                elif n == "HammerOn": d["hammer_on"] = p.find("Enable") is not None
                elif n == "Vibrato": d["vibrato"] = True
                elif n == "Slide": d["slide"] = True
                elif n == "Muted": d["dead"] = p.find("Enable") is not None
                elif n == "LetRing": d["let_ring"] = p.find("Enable") is not None
                elif n == "HarmonicType":
                    ht = p.find("HType")
                    if ht is not None: d["harmonic"] = ht.text
                elif n == "Bended":
                    d["bend"] = "full"  # Simplified
        return d
    
    def _parse_beat(self, e) -> Dict:
        d = {"notes": [], "duration": 4}
        rr = e.find("Rhythm")
        if rr is not None:
            rid = rr.get("ref")
            if rid in self._rhythms: d["duration"] = self._rhythms[rid]["duration"]
        nn = e.find("Notes")
        if nn is not None and nn.text:
            for nid in nn.text.split():
                if nid in self._notes: d["notes"].append(self._notes[nid])
        return d
    
    def _parse_voice(self, e) -> Dict:
        d = {"beats": []}
        bb = e.find("Beats")
        if bb is not None and bb.text:
            for bid in bb.text.split():
                if bid in self._beats: d["beats"].append(self._beats[bid])
        return d
    
    def _parse_bar(self, e) -> Dict:
        d = {"voices": []}
        vv = e.find("Voices")
        if vv is not None and vv.text:
            for vid in vv.text.split():
                if vid in self._voices: d["voices"].append(self._voices[vid])
        return d
    
    def _parse_track(self, e) -> Dict:
        d = {"name": self._text(e, "Name") or "Track", "instrument": 25,
             "tuning": [], "strings": 6, "bars": []}
        gm = e.find(".//GeneralMidi")
        if gm is not None:
            prog = self._text(gm, "Program")
            if prog: d["instrument"] = int(prog)
        props = e.find("Properties")
        if props:
            for p in props.findall("Property"):
                if p.get("name") == "Tuning":
                    pitches = p.find("Pitches")
                    if pitches is not None and pitches.text:
                        d["tuning"] = [int(x) for x in pitches.text.split()]
                        d["strings"] = len(d["tuning"])
        return d
    
    def _parse_master_bar(self, e) -> Dict:
        d = {"time_num": 4, "time_den": 4, "bar_ids": []}
        t = e.find("Time")
        if t is not None and t.text:
            parts = t.text.split("/")
            if len(parts) == 2: d["time_num"], d["time_den"] = int(parts[0]), int(parts[1])
        bb = e.find("Bars")
        if bb is not None and bb.text: d["bar_ids"] = bb.text.split()
        return d
    
    def _text(self, e, tag) -> Optional[str]:
        c = e.find(tag)
        return c.text.strip() if c is not None and c.text else None
    
    def to_notes_list(self, data: Dict) -> List[Dict]:
        notes = []
        for ti, track in enumerate(data["tracks"]):
            for bar in track.get("bars", []):
                for vi, voice in enumerate(bar["voices"]):
                    for bi, beat in enumerate(voice["beats"]):
                        for note in beat["notes"]:
                            nd = {"track": ti, "measure": bar["measure"], "beat": bi,
                                  "voice": vi, "string": note["string"], "fret": note["fret"],
                                  "duration": beat["duration"]}
                            for eff in ["palm_mute", "hammer_on", "vibrato", "slide", 
                                       "dead", "ghost", "let_ring"]:
                                if note.get(eff): nd[eff] = True
                            if note.get("bend"): nd["bend"] = note["bend"]
                            if note.get("harmonic"): nd["harmonic"] = note["harmonic"]
                            notes.append(nd)
        return notes


# =============================================================================
# MAIN CONTROLLER
# =============================================================================

class GuitarProController:
    """Guitar Pro Controller v3.0 - Full featured!"""
    
    def __init__(self):
        self.song: Optional[Song] = None
        self._clipboard: List[Dict] = []
    
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
    def load(self, path: str) -> Dict[str, Any]:
        """Load GP3/4/5/7/8 or MusicXML file."""
        if path.endswith('.gp'):
            return self.load_gp8(path)
        elif path.endswith('.xml') or path.endswith('.musicxml'):
            return self.load_musicxml(path)
        else:
            self.song = parse(path)
            return self.get_info()
    
    def load_gp8(self, path: str) -> Dict[str, Any]:
        """Load GP7/8 file."""
        reader = GP8Reader()
        data = reader.read(path)
        
        self.create(title=data["title"] or "Imported", artist=data["artist"], tempo=data["tempo"])
        
        for i, ti in enumerate(data["tracks"]):
            if i == 0:
                track = self.song.tracks[0]
                track.name = ti["name"]
                track.channel.instrument = ti["instrument"]
                if ti["tuning"]: self._set_tuning_from_midi(track, ti["tuning"])
            else:
                idx = self.add_track(ti["name"], instrument=ti["instrument"])
                if ti["tuning"]: self._set_tuning_from_midi(self.song.tracks[idx], ti["tuning"])
        
        nm = len(data["master_bars"])
        if nm > len(self.song.measureHeaders):
            self.add_measures(nm - len(self.song.measureHeaders))
        
        notes = reader.to_notes_list(data)
        if notes: self.add_notes_batch(notes)
        return self.get_info()
    
    def load_musicxml(self, path: str) -> Dict[str, Any]:
        """Load MusicXML file."""
        from .musicxml_handler import import_musicxml
        data = import_musicxml(path)
        
        self.create(title=data["title"] or "Imported", artist=data["artist"], tempo=data["tempo"])
        
        for i, ti in enumerate(data["tracks"]):
            if i == 0:
                track = self.song.tracks[0]
                track.name = ti["name"]
                track.channel.instrument = ti["instrument"]
                if ti["tuning"]: self._set_tuning_from_midi(track, ti["tuning"])
            else:
                idx = self.add_track(ti["name"], instrument=ti["instrument"])
                if ti["tuning"]: self._set_tuning_from_midi(self.song.tracks[idx], ti["tuning"])
            
            if ti["notes"]: self.add_notes_batch(ti["notes"])
        
        return self.get_info()
    
    def save(self, path: str) -> bool:
        """Save to GP5 or MusicXML."""
        if not self.song:
            raise ValueError("No song loaded")
        
        if path.endswith('.xml') or path.endswith('.musicxml'):
            from .musicxml_handler import export_musicxml
            export_musicxml(self.song, path)
        else:
            write(self.song, path, version=(5, 1, 0))
        return True
    
    def export_musicxml(self, path: str) -> bool:
        """Export to MusicXML."""
        if not self.song:
            raise ValueError("No song loaded")
        from .musicxml_handler import export_musicxml
        export_musicxml(self.song, path)
        return True
    
    # =========================================================================
    # SONG OPERATIONS
    # =========================================================================
    
    def create(self, title: str = "New Song", artist: str = "", 
               tempo: int = 120, tuning: str = "standard") -> Dict[str, Any]:
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
        self.song = Song()
        self.song.title = title
        self.song.artist = artist
        self.song.tempo = tempo
        
        if tracks:
            for i, t in enumerate(tracks):
                if i == 0:
                    track = self.song.tracks[0]
                    track.name = t.get("name", f"Track {i+1}")
                    track.channel.instrument = t.get("instrument", 25)
                    self._set_track_tuning(track, t.get("tuning", "standard"))
                else:
                    self.add_track(t.get("name", f"Track {i+1}"),
                                   t.get("tuning", "standard"), t.get("instrument", 25))
        else:
            self.song.tracks[0].name = "Guitar"
            self._set_track_tuning(self.song.tracks[0], "standard")
        
        if measures > len(self.song.measureHeaders):
            self.add_measures(measures - len(self.song.measureHeaders))
        if notes: self.add_notes_batch(notes)
        return self.get_info()
    
    def get_info(self) -> Dict[str, Any]:
        if not self.song: return {"error": "No song loaded"}
        return {
            "title": self.song.title, "artist": self.song.artist,
            "album": self.song.album, "tempo": self.song.tempo,
            "tracks": len(self.song.tracks),
            "measures": len(self.song.measureHeaders),
            "track_details": [
                {"index": i, "name": t.name, "strings": len(t.strings),
                 "tuning": self._get_tuning_name(t), "instrument": t.channel.instrument}
                for i, t in enumerate(self.song.tracks)
            ]
        }
    
    def set_properties(self, title: str = None, artist: str = None,
                       album: str = None, tempo: int = None) -> bool:
        if not self.song: return False
        if title is not None: self.song.title = title
        if artist is not None: self.song.artist = artist
        if album is not None: self.song.album = album
        if tempo is not None: self.song.tempo = tempo
        return True
    
    # =========================================================================
    # TRACK OPERATIONS
    # =========================================================================
    
    def add_track(self, name: str, tuning: str = "standard", instrument: int = 25) -> int:
        if not self.song: self.create()
        track = Track(self.song)
        track.name = name
        track.channel.instrument = instrument
        self._set_track_tuning(track, tuning)
        for header in self.song.measureHeaders:
            track.measures.append(Measure(track, header))
        self.song.tracks.append(track)
        return len(self.song.tracks) - 1
    
    def set_track_tuning(self, track_index: int, tuning: str) -> bool:
        if not self.song or track_index >= len(self.song.tracks): return False
        self._set_track_tuning(self.song.tracks[track_index], tuning)
        return True
    
    def get_tracks(self) -> List[Dict]:
        if not self.song: return []
        return [{"index": i, "name": t.name, "strings": len(t.strings),
                 "tuning": self._get_tuning_name(t), "instrument": t.channel.instrument,
                 "is_percussion": t.isPercussionTrack}
                for i, t in enumerate(self.song.tracks)]
    
    # =========================================================================
    # MEASURE OPERATIONS
    # =========================================================================
    
    def add_measures(self, count: int = 1) -> int:
        if not self.song: self.create()
        for _ in range(count): self._add_measure_header()
        return len(self.song.measureHeaders)
    
    def set_time_signature(self, measure: int, numerator: int, denominator: int) -> bool:
        if not self.song or measure >= len(self.song.measureHeaders): return False
        header = self.song.measureHeaders[measure]
        header.timeSignature.numerator = numerator
        header.timeSignature.denominator.value = denominator
        return True
    
    # =========================================================================
    # MARKERS / SECTIONS
    # =========================================================================
    
    def add_marker(self, measure: int, title: str, color: Tuple[int,int,int] = (255, 0, 0)) -> bool:
        """Add a section marker (e.g., 'Intro', 'Verse', 'Chorus')."""
        if not self.song or measure >= len(self.song.measureHeaders): return False
        header = self.song.measureHeaders[measure]
        header.marker = Marker(title=title, color=gp.models.Color(*color))
        return True
    
    def get_markers(self) -> List[Dict]:
        """Get all markers in the song."""
        if not self.song: return []
        markers = []
        for i, header in enumerate(self.song.measureHeaders):
            if header.marker:
                markers.append({
                    "measure": i, "title": header.marker.title,
                    "color": (header.marker.color.r, header.marker.color.g, header.marker.color.b)
                })
        return markers
    
    # =========================================================================
    # REPEAT / ENDINGS
    # =========================================================================
    
    def set_repeat_start(self, measure: int) -> bool:
        """Mark measure as repeat start."""
        if not self.song or measure >= len(self.song.measureHeaders): return False
        self.song.measureHeaders[measure].isRepeatOpen = True
        return True
    
    def set_repeat_end(self, measure: int, count: int = 2) -> bool:
        """Mark measure as repeat end with count."""
        if not self.song or measure >= len(self.song.measureHeaders): return False
        header = self.song.measureHeaders[measure]
        header.repeatClose = count
        return True
    
    def set_alternate_ending(self, measure: int, endings: List[int]) -> bool:
        """Set alternate endings (e.g., [1] for 1st ending, [2] for 2nd)."""
        if not self.song or measure >= len(self.song.measureHeaders): return False
        # Encode as bitmask
        mask = sum(1 << (e - 1) for e in endings if e > 0)
        self.song.measureHeaders[measure].repeatAlternative = mask
        return True
    
    # =========================================================================
    # TEMPO CHANGES
    # =========================================================================
    
    def set_tempo_change(self, track: int, measure: int, beat: int, new_tempo: int) -> bool:
        """Add tempo change at specific position."""
        if not self.song: return False
        if track >= len(self.song.tracks): return False
        
        track_obj = self.song.tracks[track]
        if measure >= len(track_obj.measures): return False
        
        m = track_obj.measures[measure]
        if not m.voices: return False
        
        voice = m.voices[0]
        while beat >= len(voice.beats):
            new_beat = Beat(voice)
            new_beat.duration = Duration()
            new_beat.duration.value = 4
            voice.beats.append(new_beat)
        
        b = voice.beats[beat]
        if b.effect is None:
            b.effect = BeatEffect()
        
        if b.effect.mixTableChange is None:
            b.effect.mixTableChange = MixTableChange()
        
        b.effect.mixTableChange.tempo = MixTableItem(value=new_tempo, duration=1, allTracks=True)
        return True
    
    # =========================================================================
    # NOTE OPERATIONS
    # =========================================================================
    
    def add_note(self, track: int, measure: int, beat: int, 
                 string: int, fret: int, duration: int = 4) -> bool:
        return self.add_notes_batch([{
            "track": track, "measure": measure, "beat": beat,
            "string": string, "fret": fret, "duration": duration
        }])
    
    def add_notes_batch(self, notes: List[Dict]) -> bool:
        """
        Add multiple notes with full effect support.
        
        Supported effects in note dict:
            palm_mute, hammer_on, pull_off, slide, vibrato, ghost, dead, let_ring,
            staccato, accent, heavy_accent, tap, slap, pop,
            bend (str: 'half', 'full', 'full_half', 'double' or int in quarter tones),
            bend_release (bool),
            harmonic (str: 'natural', 'artificial', 'pinch', 'tap'),
            trill (int: trill fret),
            trill_speed (int: 8, 16, 32),
            tremolo_picking (int: 8, 16, 32),
            grace_fret (int),
            grace_duration (int: 1, 2, 3 for 16th, 32nd, 64th),
            grace_transition (str: 'none', 'slide', 'bend', 'hammer'),
            tied (bool)
        """
        if not self.song: self.create()
        
        grouped: Dict[Tuple[int,int,int,int], List[Dict]] = {}
        for n in notes:
            key = (int(n.get("track", 0)), int(n.get("measure", 0)),
                   int(n.get("voice", 0)), int(n.get("beat", 0)))
            grouped.setdefault(key, []).append(n)
        
        for (ti, mi, vi, bi) in sorted(grouped.keys()):
            nl = grouped[(ti, mi, vi, bi)]
            if ti >= len(self.song.tracks): continue
            track = self.song.tracks[ti]
            
            while mi >= len(track.measures):
                self._add_measure_header()
            measure = track.measures[mi]
            
            while vi >= len(measure.voices):
                measure.voices.append(Voice(measure))
            voice = measure.voices[vi]
            
            while bi >= len(voice.beats):
                nb = Beat(voice)
                nb.duration = Duration()
                nb.duration.value = nl[0].get("duration", 4)
                nb.start = len(voice.beats) * 960
                voice.beats.append(nb)
            
            beat = voice.beats[bi]
            if beat.duration is None:
                beat.duration = Duration()
            beat.duration.value = nl[0].get("duration", 4)
            
            for n in nl:
                note = Note(beat)
                note.string = int(n["string"])
                note.value = int(n["fret"])
                
                if note.effect is None:
                    note.effect = NoteEffect()
                
                # Basic effects
                if n.get("palm_mute"): note.effect.palmMute = True
                if n.get("hammer_on") or n.get("pull_off"): note.effect.hammer = True
                if n.get("slide"): note.effect.slides = [gp.SlideType.shiftSlideTo]
                if n.get("vibrato"): note.effect.vibrato = True
                if n.get("ghost"): note.effect.ghostNote = True
                if n.get("dead"): note.type = gp.NoteType.dead
                if n.get("let_ring"): note.effect.letRing = True
                if n.get("staccato"): note.effect.staccato = True
                if n.get("accent"): note.effect.accentuatedNote = True
                if n.get("heavy_accent"): note.effect.heavyAccentuatedNote = True
                if n.get("tied"): note.type = gp.NoteType.tie
                
                # Bend
                if n.get("bend"):
                    bend_val = n["bend"]
                    if isinstance(bend_val, str):
                        bend_map = {"quarter": 25, "half": 50, "full": 100, 
                                   "full_half": 150, "double": 200}
                        bend_val = bend_map.get(bend_val, 100)
                    
                    bend = BendEffect()
                    bend.type = BendType.bend
                    bend.value = bend_val
                    # Create bend curve: start -> peak
                    bend.points = [
                        BendPoint(position=0, value=0),
                        BendPoint(position=6, value=bend_val)
                    ]
                    if n.get("bend_release"):
                        bend.points.append(BendPoint(position=12, value=0))
                    note.effect.bend = bend
                
                # Harmonic
                if n.get("harmonic"):
                    h_type = n["harmonic"]
                    if h_type == "natural":
                        note.effect.harmonic = NaturalHarmonic()
                    elif h_type == "artificial":
                        note.effect.harmonic = ArtificialHarmonic()
                    elif h_type == "pinch":
                        note.effect.harmonic = PinchHarmonic()
                    elif h_type == "tap":
                        note.effect.harmonic = TappedHarmonic(fret=n.get("fret", 12))
                
                # Trill
                if n.get("trill"):
                    trill = TrillEffect()
                    trill.fret = int(n["trill"])
                    trill.duration = Duration()
                    trill.duration.value = n.get("trill_speed", 16)
                    note.effect.trill = trill
                
                # Tremolo picking
                if n.get("tremolo_picking"):
                    tp = TremoloPickingEffect()
                    tp.duration = Duration()
                    tp.duration.value = int(n["tremolo_picking"])
                    note.effect.tremoloPicking = tp
                
                # Grace note
                if n.get("grace_fret") is not None:
                    grace = GraceEffect()
                    grace.fret = int(n["grace_fret"])
                    grace.velocity = n.get("grace_velocity", 95)
                    grace.duration = n.get("grace_duration", 1)  # 1=16th, 2=32nd, 3=64th
                    grace.isOnBeat = n.get("grace_on_beat", False)
                    
                    trans = n.get("grace_transition", "none")
                    trans_map = {
                        "none": GraceEffectTransition.none,
                        "slide": GraceEffectTransition.slide,
                        "bend": GraceEffectTransition.bend,
                        "hammer": GraceEffectTransition.hammer
                    }
                    grace.transition = trans_map.get(trans, GraceEffectTransition.none)
                    note.effect.grace = grace
                
                beat.notes.append(note)
            
            # Beat-level effects (tap/slap/pop)
            if beat.effect is None:
                beat.effect = BeatEffect()
            
            for n in nl:
                if n.get("tap"):
                    beat.effect.slapEffect = SlapEffect.tapping
                elif n.get("slap"):
                    beat.effect.slapEffect = SlapEffect.slapping
                elif n.get("pop"):
                    beat.effect.slapEffect = SlapEffect.popping
        
        return True
    
    # =========================================================================
    # CONVENIENCE METHODS FOR EFFECTS
    # =========================================================================
    
    def add_bend(self, track: int, measure: int, beat: int, string: int, fret: int,
                 bend_type: str = "full", release: bool = False, duration: int = 4) -> bool:
        """Add a note with bend. bend_type: 'half', 'full', 'full_half', 'double'"""
        return self.add_notes_batch([{
            "track": track, "measure": measure, "beat": beat, "string": string,
            "fret": fret, "duration": duration, "bend": bend_type, "bend_release": release
        }])
    
    def add_harmonic(self, track: int, measure: int, beat: int, string: int, fret: int,
                     harmonic_type: str = "natural", duration: int = 4) -> bool:
        """Add harmonic. Type: 'natural', 'artificial', 'pinch', 'tap'"""
        return self.add_notes_batch([{
            "track": track, "measure": measure, "beat": beat, "string": string,
            "fret": fret, "duration": duration, "harmonic": harmonic_type
        }])
    
    def add_trill(self, track: int, measure: int, beat: int, string: int, 
                  fret: int, trill_fret: int, speed: int = 16, duration: int = 4) -> bool:
        """Add trill between fret and trill_fret. Speed: 8, 16, 32"""
        return self.add_notes_batch([{
            "track": track, "measure": measure, "beat": beat, "string": string,
            "fret": fret, "duration": duration, "trill": trill_fret, "trill_speed": speed
        }])
    
    def add_tremolo_picking(self, track: int, measure: int, beat: int, string: int,
                            fret: int, speed: int = 16, duration: int = 4) -> bool:
        """Add tremolo picked note. Speed: 8, 16, 32"""
        return self.add_notes_batch([{
            "track": track, "measure": measure, "beat": beat, "string": string,
            "fret": fret, "duration": duration, "tremolo_picking": speed
        }])
    
    def add_grace_note(self, track: int, measure: int, beat: int, string: int,
                       fret: int, grace_fret: int, transition: str = "hammer",
                       duration: int = 4) -> bool:
        """Add note with grace note. Transition: 'none', 'slide', 'bend', 'hammer'"""
        return self.add_notes_batch([{
            "track": track, "measure": measure, "beat": beat, "string": string,
            "fret": fret, "duration": duration, "grace_fret": grace_fret,
            "grace_transition": transition
        }])
    
    # =========================================================================
    # TAB IMPORT
    # =========================================================================
    
    def import_tab_bulk(self, tab: str, track: int = 0, 
                        start_measure: int = 0, duration: int = 8) -> Dict[str, Any]:
        if not self.song: self.create()
        tab = tab.strip()
        if '|' in tab and any(c in tab.lower() for c in 'ebgdae'):
            notes = self._parse_standard_tab(tab, track, start_measure, duration)
        else:
            notes = self._parse_compact_tab(tab, track, start_measure, duration)
        if notes: self.add_notes_batch(notes)
        return {"notes_added": len(notes)}
    
    def _parse_standard_tab(self, tab: str, track: int, start_measure: int, duration: int) -> List[Dict]:
        notes = []
        lines = tab.strip().split('\n')
        tab_lines = []
        for line in lines:
            line = line.strip()
            match = re.match(r'^([eEbBgGdDaA])\s*\|(.*)$', line)
            if match:
                sc = match.group(1).upper()
                content = match.group(2)
                sm = {'B': 2, 'G': 3, 'D': 4, 'A': 5}
                sn = 1 if sc == 'E' and len(tab_lines) == 0 else (6 if sc == 'E' else sm.get(sc, 1))
                tab_lines.append((sn, content))
        
        if not tab_lines: return notes
        
        max_len = max(len(c) for _, c in tab_lines)
        cm, cb = start_measure, 0
        bpm = 8 if duration == 8 else 4
        col = 0
        
        while col < max_len:
            if all(col < len(c) and c[col] == '|' for _, c in tab_lines):
                col += 1
                continue
            
            cn = []
            mfl = 1
            for sn, content in tab_lines:
                if col >= len(content): continue
                ch = content[col]
                if ch.isdigit():
                    fs = ch
                    if col + 1 < len(content) and content[col + 1].isdigit():
                        fs += content[col + 1]
                        mfl = 2
                    cn.append({"track": track, "measure": cm, "beat": cb,
                               "string": sn, "fret": int(fs), "duration": duration})
            
            if cn:
                notes.extend(cn)
                cb += 1
                if cb >= bpm: cb, cm = 0, cm + 1
            
            col += mfl
            while col < max_len and not any(
                col < len(c) and (c[col].isdigit() or c[col] == '|') for _, c in tab_lines
            ): col += 1
        
        return notes
    
    def _parse_compact_tab(self, tab: str, track: int, start_measure: int, duration: int) -> List[Dict]:
        notes = []
        cb, cm = 0, start_measure
        bpm = 8 if duration == 8 else 4
        
        for part in tab.strip().split():
            if ':' in part:
                ss, fs = part.split(':', 1)
                string = int(ss)
                for f in fs.split('-'):
                    f = f.strip()
                    if f.lstrip('-').isdigit() or f == '0':
                        notes.append({"track": track, "measure": cm, "beat": cb,
                                      "string": string, "fret": int(f), "duration": duration})
                        cb += 1
                        if cb >= bpm: cb, cm = 0, cm + 1
        return notes
    
    # =========================================================================
    # COPY/PASTE
    # =========================================================================
    
    def copy_measures(self, track_index: int, start_measure: int, end_measure: int) -> Dict[str, Any]:
        if not self.song or track_index >= len(self.song.tracks):
            return {"error": "Invalid track"}
        track = self.song.tracks[track_index]
        self._clipboard = []
        for mi in range(start_measure, min(end_measure + 1, len(track.measures))):
            m = track.measures[mi]
            for voice in m.voices:
                for bi, beat in enumerate(voice.beats):
                    for note in beat.notes:
                        nd = {"measure": mi - start_measure, "beat": bi,
                              "string": note.string, "fret": note.value,
                              "duration": beat.duration.value if beat.duration else 4}
                        if note.effect:
                            if note.effect.palmMute: nd["palm_mute"] = True
                            if note.effect.hammer: nd["hammer_on"] = True
                            if note.effect.bend: nd["bend"] = "full"
                        self._clipboard.append(nd)
        return {"notes_copied": len(self._clipboard)}
    
    def paste_measures(self, track_index: int, start_measure: int, repeat: int = 1) -> Dict[str, Any]:
        if not self._clipboard: return {"error": "Empty"}
        if not self.song: self.create()
        pm = max(n["measure"] for n in self._clipboard) + 1
        nta = []
        for rep in range(repeat):
            for n in self._clipboard:
                nta.append({**n, "track": track_index, 
                           "measure": start_measure + n["measure"] + rep * pm})
        tn = start_measure + pm * repeat
        while len(self.song.measureHeaders) < tn:
            self._add_measure_header()
        self.add_notes_batch(nta)
        return {"notes_added": len(nta)}
    
    def repeat_pattern(self, track_index: int, source_start: int, source_end: int,
                       dest_start: int, times: int = 1) -> Dict[str, Any]:
        self.copy_measures(track_index, source_start, source_end)
        return self.paste_measures(track_index, dest_start, times)
    
    def copy_track_from_file(self, source_path: str, source_track_index: int,
                             dest_track_name: str = None, start_measure: int = 0, 
                             end_measure: int = None) -> Dict[str, Any]:
        if not self.song: self.create()
        
        if source_path.endswith('.gp'):
            reader = GP8Reader()
            data = reader.read(source_path)
            if source_track_index >= len(data["tracks"]):
                return {"error": "Track not found"}
            
            st = data["tracks"][source_track_index]
            tn = dest_track_name or st["name"]
            nti = self.add_track(tn, instrument=st["instrument"])
            if st["tuning"]:
                self._set_tuning_from_midi(self.song.tracks[nti], st["tuning"])
            
            notes = reader.to_notes_list(data)
            notes = [n for n in notes if n["track"] == source_track_index]
            for n in notes: n["track"] = nti
            
            if end_measure is not None:
                notes = [n for n in notes if start_measure <= n["measure"] <= end_measure]
                for n in notes: n["measure"] -= start_measure
            
            mn = max((n["measure"] for n in notes), default=0) + 1
            while len(self.song.measureHeaders) < mn:
                self._add_measure_header()
            
            self.add_notes_batch(notes)
            return {"track_index": nti, "notes_copied": len(notes)}
        
        ss = parse(source_path)
        if source_track_index >= len(ss.tracks):
            return {"error": "Track not found"}
        st = ss.tracks[source_track_index]
        if end_measure is None:
            end_measure = len(st.measures) - 1
        
        tn = dest_track_name or st.name
        nti = self.add_track(tn, self._get_tuning_name(st), st.channel.instrument)
        nt = self.song.tracks[nti]
        nt.strings = [GuitarString(number=s.number, value=s.value) for s in st.strings]
        
        mn = end_measure - start_measure + 1
        while len(self.song.measureHeaders) < mn:
            self._add_measure_header()
        
        nta = []
        for mi in range(start_measure, min(end_measure + 1, len(st.measures))):
            for vi, voice in enumerate(st.measures[mi].voices):
                for bi, beat in enumerate(voice.beats):
                    for note in beat.notes:
                        nd = {"track": nti, "measure": mi - start_measure, "beat": bi,
                              "voice": vi, "string": note.string, "fret": note.value,
                              "duration": beat.duration.value if beat.duration else 4}
                        if note.effect:
                            if note.effect.palmMute: nd["palm_mute"] = True
                            if note.effect.hammer: nd["hammer_on"] = True
                        nta.append(nd)
        
        if nta: self.add_notes_batch(nta)
        return {"track_index": nti, "notes_copied": len(nta)}
    
    # =========================================================================
    # CHORDS
    # =========================================================================
    
    def add_chord_by_name(self, track: int, measure: int, beat: int,
                          chord_name: str, duration: int = 4) -> bool:
        if chord_name not in CHORDS: return False
        return self.add_chord(track, measure, beat, CHORDS[chord_name], duration)
    
    def add_chord(self, track: int, measure: int, beat: int,
                  frets: List[int], duration: int = 4) -> bool:
        notes = [{"track": track, "measure": measure, "beat": beat,
                  "string": 6 - i, "fret": f, "duration": duration}
                 for i, f in enumerate(frets) if f >= 0]
        return self.add_notes_batch(notes)
    
    def add_power_chord(self, track: int, measure: int, beat: int,
                        root_string: int, root_fret: int, duration: int = 4) -> bool:
        return self.add_notes_batch([
            {"track": track, "measure": measure, "beat": beat,
             "string": root_string, "fret": root_fret, "duration": duration},
            {"track": track, "measure": measure, "beat": beat,
             "string": root_string - 1, "fret": root_fret + 2, "duration": duration},
            {"track": track, "measure": measure, "beat": beat,
             "string": root_string - 2, "fret": root_fret + 2, "duration": duration},
        ])
    
    def add_chord_progression(self, track: int, start_measure: int, chords: List[str],
                              beats_per_chord: int = 4, duration: int = 4) -> Dict[str, Any]:
        cm, cb, ca = start_measure, 0, 0
        for cn in chords:
            if cn in CHORDS:
                while cm >= len(self.song.measureHeaders):
                    self._add_measure_header()
                self.add_chord_by_name(track, cm, cb, cn, duration)
                ca += 1
            cb += beats_per_chord
            while cb >= 4: cb, cm = cb - 4, cm + 1
        return {"chords_added": ca}
    
    def list_chords(self) -> List[str]:
        return list(CHORDS.keys())
    
    # =========================================================================
    # RIFF TEMPLATES
    # =========================================================================
    
    def list_riff_templates(self) -> Dict[str, str]:
        return {n: t["description"] for n, t in RIFF_TEMPLATES.items()}
    
    def add_riff_template(self, track: int, measure: int, template_name: str,
                          root_fret: int = 0, repeat: int = 1) -> Dict[str, Any]:
        if template_name not in RIFF_TEMPLATES:
            return {"error": f"Unknown: {template_name}"}
        t = RIFF_TEMPLATES[template_name]
        while len(self.song.measureHeaders) < measure + repeat:
            self._add_measure_header()
        nta = [{"track": track, "measure": measure + rep, "beat": nt["beat"],
                "string": nt["string"], "fret": nt["fret"] + root_fret,
                "duration": t["duration"], "palm_mute": nt.get("palm_mute", False)}
               for rep in range(repeat) for nt in t["pattern"]]
        self.add_notes_batch(nta)
        return {"notes_added": len(nta)}
    
    # =========================================================================
    # TRANSPOSE
    # =========================================================================
    
    def transpose_track(self, track_index: int, semitones: int,
                        start_measure: int = 0, end_measure: int = None) -> Dict[str, Any]:
        if not self.song or track_index >= len(self.song.tracks):
            return {"error": "Invalid track"}
        track = self.song.tracks[track_index]
        if end_measure is None:
            end_measure = len(track.measures) - 1
        nt = 0
        for mi in range(start_measure, min(end_measure + 1, len(track.measures))):
            for voice in track.measures[mi].voices:
                for beat in voice.beats:
                    for note in beat.notes:
                        nf = note.value + semitones
                        if 0 <= nf <= 24:
                            note.value = nf
                            nt += 1
        return {"notes_transposed": nt}
    
    # =========================================================================
    # OUTPUT
    # =========================================================================
    
    def get_tab(self, track_index: int, start_measure: int = 0, end_measure: int = None) -> str:
        if not self.song or track_index >= len(self.song.tracks):
            return "Invalid"
        track = self.song.tracks[track_index]
        ns = len(track.strings)
        if end_measure is None:
            end_measure = len(track.measures)
        sn = [self._note_name(s.value) for s in sorted(track.strings, key=lambda s: s.number)]
        tl = [f"{n}|" for n in sn]
        for mi in range(start_measure, min(end_measure, len(track.measures))):
            bd = [{note.string: note.value for note in beat.notes}
                  for voice in track.measures[mi].voices for beat in voice.beats] or [{}]
            for nd in bd:
                for snum in range(1, ns + 1):
                    li = ns - snum
                    tl[li] += str(nd[snum]).ljust(3, '-') if snum in nd else "---"
            for i in range(ns): tl[i] += "|"
        return '\n'.join(tl)
    
    def get_track_notes(self, track_index: int) -> List[Dict]:
        if not self.song or track_index >= len(self.song.tracks): return []
        track = self.song.tracks[track_index]
        return [{"measure": mi, "beat": bi, "voice": vi, "string": note.string,
                 "fret": note.value, "duration": beat.duration.value if beat.duration else 4}
                for mi, m in enumerate(track.measures)
                for vi, voice in enumerate(m.voices)
                for bi, beat in enumerate(voice.beats)
                for note in beat.notes]
    
    def get_statistics(self) -> Dict[str, Any]:
        if not self.song: return {}
        ts = []
        tn = 0
        for i, track in enumerate(self.song.tracks):
            cnt = sum(len(beat.notes) for m in track.measures for v in m.voices for beat in v.beats)
            tn += cnt
            ts.append({"name": track.name, "notes": cnt, "measures": len(track.measures)})
        return {"title": self.song.title, "total_notes": tn, "tracks": ts,
                "measures": len(self.song.measureHeaders), "tempo": self.song.tempo}
    
    # =========================================================================
    # INTERNAL
    # =========================================================================
    
    def _set_track_tuning(self, track: Track, tuning: str):
        if tuning not in TUNINGS: tuning = "standard"
        mv = TUNINGS[tuning]
        track.strings = [GuitarString(number=i+1, value=v) for i, v in enumerate(reversed(mv))]
    
    def _set_tuning_from_midi(self, track: Track, midi_values: List[int]):
        track.strings = [GuitarString(number=i+1, value=v) for i, v in enumerate(midi_values)]
    
    def _get_tuning_name(self, track: Track) -> str:
        if not track.strings: return "unknown"
        vals = [s.value for s in sorted(track.strings, key=lambda s: -s.number)]
        for name, preset in TUNINGS.items():
            if vals == preset: return name
        return "custom"
    
    def _add_measure_header(self) -> int:
        header = MeasureHeader()
        header.timeSignature = TimeSignature()
        header.timeSignature.numerator = 4
        header.timeSignature.denominator.value = 4
        self.song.measureHeaders.append(header)
        for track in self.song.tracks:
            track.measures.append(Measure(track, header))
        return len(self.song.measureHeaders) - 1
    
    def _note_name(self, midi: int) -> str:
        return NOTE_NAMES[midi % 12]


# =============================================================================
# SINGLETON
# =============================================================================

_controller: Optional[GuitarProController] = None

def get_controller() -> GuitarProController:
    global _controller
    if _controller is None:
        _controller = GuitarProController()
    return _controller