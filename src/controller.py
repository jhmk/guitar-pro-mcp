"""
Guitar Pro Controller v2.5
NEW: GP7/8 (.gp) Read Support!

FEATURES:
- Read/Write GP3/4/5
- READ GP7/8 (via gp8_reader module)
- Batch operations, TAB import, chords, templates, transpose
"""

import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple

import guitarpro as gp
from guitarpro import parse, write
from guitarpro.models import (
    Song, Track, Measure, MeasureHeader, Voice, Beat, Note,
    Duration, TimeSignature, NoteEffect, GuitarString
)

logger = logging.getLogger(__name__)

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


# =============================================================================
# GP7/8 READER (embedded)
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
        """Read a GP7/8 file and return structured data."""
        with zipfile.ZipFile(path, 'r') as z:
            if 'VERSION' in z.namelist():
                self.version = z.read('VERSION').decode('utf-8').strip()
            
            gpif_path = 'Content/score.gpif'
            if gpif_path not in z.namelist():
                raise ValueError("Invalid GP7/8 file: missing score.gpif")
            
            self.gpif_root = ET.fromstring(z.read(gpif_path))
        
        return self._parse_gpif()
    
    def _parse_gpif(self) -> Dict[str, Any]:
        root = self.gpif_root
        result = {
            "format_version": self.version,
            "gp_version": self._text(root, "GPVersion"),
            "title": "", "artist": "", "album": "",
            "tempo": 120, "tracks": [], "master_bars": [],
        }
        
        score = root.find("Score")
        if score is not None:
            result["title"] = self._text(score, "Title") or ""
            result["artist"] = self._text(score, "Artist") or ""
            result["album"] = self._text(score, "Album") or ""
        
        # Tempo from MasterTrack/Automations
        mt = root.find("MasterTrack")
        if mt is not None:
            autos = mt.find("Automations")
            if autos is not None:
                for a in autos.findall("Automation"):
                    if self._text(a, "Type") == "Tempo":
                        v = self._text(a, "Value")
                        if v:
                            result["tempo"] = int(float(v.split()[0]))
                            break
        
        self._build_lookups(root)
        
        # Tracks
        tracks_elem = root.find("Tracks")
        if tracks_elem is not None:
            for t in tracks_elem.findall("Track"):
                result["tracks"].append(self._parse_track(t))
        
        # MasterBars
        mbs = root.find("MasterBars")
        if mbs is not None:
            for mb in mbs.findall("MasterBar"):
                result["master_bars"].append(self._parse_master_bar(mb))
        
        # Link bars to tracks
        for mb_idx, mb in enumerate(result["master_bars"]):
            for track_idx, bar_id in enumerate(mb["bar_ids"]):
                if track_idx < len(result["tracks"]) and bar_id in self._bars:
                    result["tracks"][track_idx].setdefault("bars", []).append({
                        "measure": mb_idx,
                        "time_num": mb["time_num"],
                        "time_den": mb["time_den"],
                        "voices": self._bars[bar_id]["voices"]
                    })
        
        return result
    
    def _build_lookups(self, root):
        # Rhythms
        rhythms = root.find("Rhythms")
        if rhythms is not None:
            for r in rhythms.findall("Rhythm"):
                self._rhythms[r.get("id")] = self._parse_rhythm(r)
        
        # Notes
        notes = root.find("Notes")
        if notes is not None:
            for n in notes.findall("Note"):
                self._notes[n.get("id")] = self._parse_note(n)
        
        # Beats
        beats = root.find("Beats")
        if beats is not None:
            for b in beats.findall("Beat"):
                self._beats[b.get("id")] = self._parse_beat(b)
        
        # Voices
        voices = root.find("Voices")
        if voices is not None:
            for v in voices.findall("Voice"):
                self._voices[v.get("id")] = self._parse_voice(v)
        
        # Bars
        bars = root.find("Bars")
        if bars is not None:
            for b in bars.findall("Bar"):
                self._bars[b.get("id")] = self._parse_bar(b)
    
    def _parse_rhythm(self, elem) -> Dict:
        dur_map = {"Whole": 1, "Half": 2, "Quarter": 4, "Eighth": 8, "16th": 16, "32nd": 32}
        nv = elem.find("NoteValue")
        dur = dur_map.get(nv.text if nv is not None else "Quarter", 4)
        dot = elem.find("AugmentationDot")
        return {"duration": dur, "dotted": dot is not None}
    
    def _parse_note(self, elem) -> Dict:
        data = {"fret": 0, "string": 1, "palm_mute": False, "hammer_on": False,
                "vibrato": False, "slide": False, "dead": False, "ghost": False, "let_ring": False}
        props = elem.find("Properties")
        if props is not None:
            for p in props.findall("Property"):
                name = p.get("name")
                if name == "Fret":
                    f = p.find("Fret")
                    if f is not None and f.text: data["fret"] = int(f.text)
                elif name == "String":
                    s = p.find("String")
                    if s is not None and s.text: data["string"] = int(s.text) + 1
                elif name == "PalmMuted": data["palm_mute"] = p.find("Enable") is not None
                elif name == "HammerOn": data["hammer_on"] = p.find("Enable") is not None
                elif name == "Vibrato": data["vibrato"] = True
                elif name == "Slide": data["slide"] = True
                elif name == "Muted": data["dead"] = p.find("Enable") is not None
                elif name == "LetRing": data["let_ring"] = p.find("Enable") is not None
        aa = elem.find("AntiAccent")
        if aa is not None and aa.text == "Normal": data["ghost"] = True
        return data
    
    def _parse_beat(self, elem) -> Dict:
        data = {"notes": [], "duration": 4}
        rr = elem.find("Rhythm")
        if rr is not None:
            rid = rr.get("ref")
            if rid in self._rhythms: data["duration"] = self._rhythms[rid]["duration"]
        nn = elem.find("Notes")
        if nn is not None and nn.text:
            for nid in nn.text.split():
                if nid in self._notes: data["notes"].append(self._notes[nid])
        return data
    
    def _parse_voice(self, elem) -> Dict:
        data = {"beats": []}
        bb = elem.find("Beats")
        if bb is not None and bb.text:
            for bid in bb.text.split():
                if bid in self._beats: data["beats"].append(self._beats[bid])
        return data
    
    def _parse_bar(self, elem) -> Dict:
        data = {"voices": []}
        vv = elem.find("Voices")
        if vv is not None and vv.text:
            for vid in vv.text.split():
                if vid in self._voices: data["voices"].append(self._voices[vid])
        return data
    
    def _parse_track(self, elem) -> Dict:
        data = {"name": self._text(elem, "Name") or "Track", "instrument": 25,
                "tuning": [], "strings": 6, "capo": 0, "bars": []}
        gm = elem.find(".//GeneralMidi")
        if gm is not None:
            prog = self._text(gm, "Program")
            if prog: data["instrument"] = int(prog)
        props = elem.find("Properties")
        if props is not None:
            for p in props.findall("Property"):
                if p.get("name") == "Tuning":
                    pitches = p.find("Pitches")
                    if pitches is not None and pitches.text:
                        data["tuning"] = [int(x) for x in pitches.text.split()]
                        data["strings"] = len(data["tuning"])
                elif p.get("name") == "CapoFret":
                    f = p.find("Fret")
                    if f is not None and f.text: data["capo"] = int(f.text)
        return data
    
    def _parse_master_bar(self, elem) -> Dict:
        data = {"time_num": 4, "time_den": 4, "bar_ids": []}
        t = elem.find("Time")
        if t is not None and t.text:
            parts = t.text.split("/")
            if len(parts) == 2:
                data["time_num"], data["time_den"] = int(parts[0]), int(parts[1])
        bb = elem.find("Bars")
        if bb is not None and bb.text: data["bar_ids"] = bb.text.split()
        return data
    
    def _text(self, elem, tag) -> Optional[str]:
        c = elem.find(tag)
        return c.text.strip() if c is not None and c.text else None
    
    def to_notes_list(self, data: Dict) -> List[Dict]:
        """Convert to flat notes list for add_notes_batch()."""
        notes = []
        for ti, track in enumerate(data["tracks"]):
            for bar in track.get("bars", []):
                for vi, voice in enumerate(bar["voices"]):
                    for bi, beat in enumerate(voice["beats"]):
                        for note in beat["notes"]:
                            nd = {"track": ti, "measure": bar["measure"], "beat": bi,
                                  "voice": vi, "string": note["string"], "fret": note["fret"],
                                  "duration": beat["duration"]}
                            for eff in ["palm_mute", "hammer_on", "vibrato", "slide", "dead", "ghost", "let_ring"]:
                                if note.get(eff): nd[eff] = True
                            notes.append(nd)
        return notes


# =============================================================================
# MAIN CONTROLLER
# =============================================================================

class GuitarProController:
    """Guitar Pro Controller v2.3 - Now with GP7/8 read support!"""
    
    def __init__(self):
        self.song: Optional[Song] = None
        self._clipboard: List[Dict] = []
    
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
    def load(self, path: str) -> Dict[str, Any]:
        """Load GP3/4/5/7/8 file. Auto-detects format."""
        if path.endswith('.gp'):
            return self.load_gp8(path)
        else:
            self.song = parse(path)
            return self.get_info()
    
    def load_gp8(self, path: str) -> Dict[str, Any]:
        """
        Load GP7/8 file and convert to internal song.
        
        Note: Loads into PyGuitarPro format, some GP7/8 specific features may be lost.
        """
        reader = GP8Reader()
        data = reader.read(path)
        
        # Create new song
        self.create(
            title=data["title"] or "Imported Song",
            artist=data["artist"],
            tempo=data["tempo"]
        )
        
        # Create tracks
        for i, track_info in enumerate(data["tracks"]):
            if i == 0:
                # Modify default track
                track = self.song.tracks[0]
                track.name = track_info["name"]
                track.channel.instrument = track_info["instrument"]
                if track_info["tuning"]:
                    self._set_tuning_from_midi(track, track_info["tuning"])
            else:
                # Add new track
                idx = self.add_track(
                    name=track_info["name"],
                    instrument=track_info["instrument"]
                )
                if track_info["tuning"]:
                    self._set_tuning_from_midi(self.song.tracks[idx], track_info["tuning"])
        
        # Add measures
        num_measures = len(data["master_bars"])
        current = len(self.song.measureHeaders)
        if num_measures > current:
            self.add_measures(num_measures - current)
        
        # Set time signatures
        for i, mb in enumerate(data["master_bars"]):
            if i < len(self.song.measureHeaders):
                self.set_time_signature(i, mb["time_num"], mb["time_den"])
        
        # Add all notes
        notes = reader.to_notes_list(data)
        if notes:
            self.add_notes_batch(notes)
        
        return self.get_info()
    
    def save(self, path: str) -> bool:
        """Save to GP5 format (GP8 can open this)."""
        if not self.song:
            raise ValueError("No song loaded")
        write(self.song, path, version=(5, 1, 0))
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
                                   t.get("tuning", "standard"),
                                   t.get("instrument", 25))
        else:
            self.song.tracks[0].name = "Guitar"
            self._set_track_tuning(self.song.tracks[0], "standard")
        
        current = len(self.song.measureHeaders)
        if measures > current:
            self.add_measures(measures - current)
        
        if notes:
            self.add_notes_batch(notes)
        return self.get_info()
    
    def get_info(self) -> Dict[str, Any]:
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
                {"index": i, "name": t.name, "strings": len(t.strings),
                 "tuning": self._get_tuning_name(t), "instrument": t.channel.instrument}
                for i, t in enumerate(self.song.tracks)
            ]
        }
    
    def set_properties(self, title: str = None, artist: str = None,
                       album: str = None, tempo: int = None) -> bool:
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
    
    def add_track(self, name: str, tuning: str = "standard", instrument: int = 25) -> int:
        if not self.song:
            self.create()
        track = Track(self.song)
        track.name = name
        track.channel.instrument = instrument
        self._set_track_tuning(track, tuning)
        for header in self.song.measureHeaders:
            track.measures.append(Measure(track, header))
        self.song.tracks.append(track)
        return len(self.song.tracks) - 1
    
    def set_track_tuning(self, track_index: int, tuning: str) -> bool:
        if not self.song or track_index >= len(self.song.tracks):
            return False
        self._set_track_tuning(self.song.tracks[track_index], tuning)
        return True
    
    def get_tracks(self) -> List[Dict]:
        if not self.song:
            return []
        return [
            {"index": i, "name": t.name, "strings": len(t.strings),
             "tuning": self._get_tuning_name(t), "instrument": t.channel.instrument,
             "is_percussion": t.isPercussionTrack}
            for i, t in enumerate(self.song.tracks)
        ]
    
    # =========================================================================
    # MEASURE OPERATIONS
    # =========================================================================
    
    def add_measures(self, count: int = 1) -> int:
        if not self.song:
            self.create()
        for _ in range(count):
            self._add_measure_header()
        return len(self.song.measureHeaders)
    
    def set_time_signature(self, measure: int, numerator: int, denominator: int) -> bool:
        if not self.song or measure >= len(self.song.measureHeaders):
            return False
        header = self.song.measureHeaders[measure]
        header.timeSignature.numerator = numerator
        header.timeSignature.denominator.value = denominator
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
        if not self.song:
            self.create()
        
        grouped: Dict[Tuple[int, int, int, int], List[Dict]] = {}
        for n in notes:
            key = (int(n.get("track", 0)), int(n.get("measure", 0)),
                   int(n.get("voice", 0)), int(n.get("beat", 0)))
            grouped.setdefault(key, []).append(n)
        
        for (track_idx, measure_idx, voice_idx, beat_idx) in sorted(grouped.keys()):
            note_list = grouped[(track_idx, measure_idx, voice_idx, beat_idx)]
            
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
                new_beat.start = len(voice.beats) * 960
                voice.beats.append(new_beat)
            
            beat = voice.beats[beat_idx]
            if beat.duration is None:
                beat.duration = Duration()
            beat.duration.value = note_list[0].get("duration", 4)
            
            for n in note_list:
                note = Note(beat)
                note.string = int(n["string"])
                note.value = int(n["fret"])
                if note.effect is None:
                    note.effect = NoteEffect()
                if n.get("palm_mute"): note.effect.palmMute = True
                if n.get("hammer_on") or n.get("pull_off"): note.effect.hammer = True
                if n.get("slide"): note.effect.slides = [gp.SlideType.shiftSlideTo]
                if n.get("vibrato"): note.effect.vibrato = True
                if n.get("ghost"): note.effect.ghostNote = True
                if n.get("dead"): note.type = gp.NoteType.dead
                if n.get("let_ring"): note.effect.letRing = True
                beat.notes.append(note)
        
        return True
    
    # =========================================================================
    # TAB IMPORT
    # =========================================================================
    
    def import_tab_bulk(self, tab: str, track: int = 0, 
                        start_measure: int = 0, duration: int = 8) -> Dict[str, Any]:
        if not self.song:
            self.create()
        tab = tab.strip()
        if '|' in tab and any(c in tab.lower() for c in 'ebgdae'):
            notes = self._parse_standard_tab(tab, track, start_measure, duration)
        else:
            notes = self._parse_compact_tab(tab, track, start_measure, duration)
        if notes:
            self.add_notes_batch(notes)
        return {"notes_added": len(notes), "measures_used": self._count_measures(notes)}
    
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
        
        if not tab_lines:
            return notes
        
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
                if col >= len(content):
                    continue
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
                if cb >= bpm:
                    cb = 0
                    cm += 1
            
            col += mfl
            while col < max_len and not any(
                col < len(c) and (c[col].isdigit() or c[col] == '|') for _, c in tab_lines
            ):
                col += 1
        
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
                        if cb >= bpm:
                            cb = 0
                            cm += 1
        return notes
    
    def _count_measures(self, notes: List[Dict]) -> int:
        return max((n.get("measure", 0) for n in notes), default=-1) + 1 if notes else 0
    
    # =========================================================================
    # PATTERN COPY/PASTE
    # =========================================================================
    
    def copy_measures(self, track_index: int, start_measure: int, end_measure: int) -> Dict[str, Any]:
        if not self.song or track_index >= len(self.song.tracks):
            return {"error": "Invalid track"}
        track = self.song.tracks[track_index]
        self._clipboard = []
        for m_idx in range(start_measure, min(end_measure + 1, len(track.measures))):
            measure = track.measures[m_idx]
            for voice in measure.voices:
                for b_idx, beat in enumerate(voice.beats):
                    for note in beat.notes:
                        nd = {"measure": m_idx - start_measure, "beat": b_idx,
                              "string": note.string, "fret": note.value,
                              "duration": beat.duration.value if beat.duration else 4}
                        if note.effect and note.effect.palmMute: nd["palm_mute"] = True
                        if note.effect and note.effect.hammer: nd["hammer_on"] = True
                        self._clipboard.append(nd)
        return {"notes_copied": len(self._clipboard), "measures": end_measure - start_measure + 1}
    
    def paste_measures(self, track_index: int, start_measure: int, repeat: int = 1) -> Dict[str, Any]:
        if not self._clipboard:
            return {"error": "Clipboard empty"}
        if not self.song:
            self.create()
        pm = max(n["measure"] for n in self._clipboard) + 1
        nta = []
        for rep in range(repeat):
            off = rep * pm
            for note in self._clipboard:
                nta.append({**note, "track": track_index, "measure": start_measure + note["measure"] + off})
        tn = start_measure + (pm * repeat)
        while len(self.song.measureHeaders) < tn:
            self._add_measure_header()
        self.add_notes_batch(nta)
        return {"notes_added": len(nta), "measures_filled": pm * repeat}
    
    def repeat_pattern(self, track_index: int, source_start: int, source_end: int,
                       dest_start: int, times: int = 1) -> Dict[str, Any]:
        self.copy_measures(track_index, source_start, source_end)
        return self.paste_measures(track_index, dest_start, times)
    
    def copy_track_from_file(self, source_path: str, source_track_index: int,
                             dest_track_name: str = None, start_measure: int = 0, 
                             end_measure: int = None) -> Dict[str, Any]:
        """Copy track from another file (supports GP3-8)."""
        if not self.song:
            self.create()
        
        # Handle GP7/8 files
        if source_path.endswith('.gp'):
            reader = GP8Reader()
            data = reader.read(source_path)
            if source_track_index >= len(data["tracks"]):
                return {"error": f"Source track {source_track_index} not found"}
            
            st = data["tracks"][source_track_index]
            track_name = dest_track_name or st["name"]
            nti = self.add_track(track_name, instrument=st["instrument"])
            if st["tuning"]:
                self._set_tuning_from_midi(self.song.tracks[nti], st["tuning"])
            
            notes = reader.to_notes_list(data)
            notes = [n for n in notes if n["track"] == source_track_index]
            for n in notes:
                n["track"] = nti
            
            if end_measure is not None:
                notes = [n for n in notes if start_measure <= n["measure"] <= end_measure]
                for n in notes:
                    n["measure"] -= start_measure
            
            mn = max((n["measure"] for n in notes), default=0) + 1
            while len(self.song.measureHeaders) < mn:
                self._add_measure_header()
            
            self.add_notes_batch(notes)
            return {"track_name": track_name, "track_index": nti,
                    "notes_copied": len(notes), "measures_copied": mn}
        
        # Handle GP3-5 files
        source_song = parse(source_path)
        if source_track_index >= len(source_song.tracks):
            return {"error": f"Source track {source_track_index} not found"}
        st = source_song.tracks[source_track_index]
        if end_measure is None:
            end_measure = len(st.measures) - 1
        
        track_name = dest_track_name or st.name
        nti = self.add_track(track_name, self._get_tuning_name(st), st.channel.instrument)
        nt = self.song.tracks[nti]
        nt.strings = [GuitarString(number=s.number, value=s.value) for s in st.strings]
        
        mn = end_measure - start_measure + 1
        while len(self.song.measureHeaders) < mn:
            self._add_measure_header()
        
        nta = []
        for m_idx in range(start_measure, min(end_measure + 1, len(st.measures))):
            for v_idx, voice in enumerate(st.measures[m_idx].voices):
                for b_idx, beat in enumerate(voice.beats):
                    for note in beat.notes:
                        nd = {"track": nti, "measure": m_idx - start_measure, "beat": b_idx,
                              "voice": v_idx, "string": note.string, "fret": note.value,
                              "duration": beat.duration.value if beat.duration else 4}
                        if note.effect:
                            if note.effect.palmMute: nd["palm_mute"] = True
                            if note.effect.hammer: nd["hammer_on"] = True
                            if note.effect.vibrato: nd["vibrato"] = True
                        nta.append(nd)
        
        if nta:
            self.add_notes_batch(nta)
        return {"track_name": track_name, "track_index": nti, "notes_copied": len(nta), "measures_copied": mn}
    
    # =========================================================================
    # CHORDS
    # =========================================================================
    
    def add_chord_by_name(self, track: int, measure: int, beat: int,
                          chord_name: str, duration: int = 4) -> bool:
        if chord_name not in CHORDS:
            return False
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
            while cb >= 4:
                cb -= 4
                cm += 1
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
            return {"error": f"Unknown template: {template_name}"}
        t = RIFF_TEMPLATES[template_name]
        while len(self.song.measureHeaders) < measure + repeat:
            self._add_measure_header()
        nta = []
        for rep in range(repeat):
            for nt in t["pattern"]:
                nta.append({"track": track, "measure": measure + rep, "beat": nt["beat"],
                            "string": nt["string"], "fret": nt["fret"] + root_fret,
                            "duration": t["duration"], "palm_mute": nt.get("palm_mute", False)})
        self.add_notes_batch(nta)
        return {"notes_added": len(nta), "measures": repeat}
    
    # =========================================================================
    # MULTI-TRACK & TRANSPOSE
    # =========================================================================
    
    def add_notes_multi_track(self, notes_by_track: Dict[int, List[Dict]]) -> Dict[str, Any]:
        an = [{**n, "track": t} for t, notes in notes_by_track.items() for n in notes]
        self.add_notes_batch(an)
        return {"total_notes_added": len(an), "tracks_modified": len(notes_by_track)}
    
    def transpose_track(self, track_index: int, semitones: int,
                        start_measure: int = 0, end_measure: int = None) -> Dict[str, Any]:
        if not self.song or track_index >= len(self.song.tracks):
            return {"error": "Invalid track"}
        track = self.song.tracks[track_index]
        if end_measure is None:
            end_measure = len(track.measures) - 1
        nt = 0
        for m_idx in range(start_measure, min(end_measure + 1, len(track.measures))):
            for voice in track.measures[m_idx].voices:
                for beat in voice.beats:
                    for note in beat.notes:
                        nf = note.value + semitones
                        if 0 <= nf <= 24:
                            note.value = nf
                            nt += 1
        return {"notes_transposed": nt}
    
    def transpose_section(self, track_index: int, start_measure: int, 
                          end_measure: int, semitones: int) -> Dict[str, Any]:
        return self.transpose_track(track_index, semitones, start_measure, end_measure)
    
    def add_palm_muted_notes(self, track: int, measure: int, string: int,
                             frets: List[int], start_beat: int = 0, duration: int = 8) -> bool:
        return self.add_notes_batch([
            {"track": track, "measure": measure, "beat": start_beat + i,
             "string": string, "fret": f, "duration": duration, "palm_mute": True}
            for i, f in enumerate(frets)
        ])
    
    # =========================================================================
    # OUTPUT
    # =========================================================================
    
    def get_tab(self, track_index: int, start_measure: int = 0, end_measure: int = None) -> str:
        if not self.song or track_index >= len(self.song.tracks):
            return "Invalid track"
        track = self.song.tracks[track_index]
        ns = len(track.strings)
        if end_measure is None:
            end_measure = len(track.measures)
        sn = [self._note_name(s.value) for s in sorted(track.strings, key=lambda s: s.number)]
        tl = [f"{n}|" for n in sn]
        for m_idx in range(start_measure, min(end_measure, len(track.measures))):
            measure = track.measures[m_idx]
            bd = [{note.string: note.value for note in beat.notes}
                  for voice in measure.voices for beat in voice.beats] or [{}]
            for nd in bd:
                for snum in range(1, ns + 1):
                    li = ns - snum
                    tl[li] += str(nd[snum]).ljust(3, '-') if snum in nd else "---"
            for i in range(ns):
                tl[i] += "|"
        return '\n'.join(tl)
    
    def get_track_notes(self, track_index: int) -> List[Dict]:
        if not self.song or track_index >= len(self.song.tracks):
            return []
        track = self.song.tracks[track_index]
        return [
            {"measure": m_idx, "beat": b_idx, "voice": v_idx,
             "string": note.string, "fret": note.value,
             "duration": beat.duration.value if beat.duration else 4}
            for m_idx, measure in enumerate(track.measures)
            for v_idx, voice in enumerate(measure.voices)
            for b_idx, beat in enumerate(voice.beats)
            for note in beat.notes
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        if not self.song:
            return {}
        ts = []
        tn = 0
        for i, track in enumerate(self.song.tracks):
            cnt = sum(len(beat.notes) for m in track.measures for v in m.voices for beat in v.beats)
            tn += cnt
            ts.append({"name": track.name, "notes": cnt, "measures": len(track.measures)})
        return {"title": self.song.title, "total_notes": tn,
                "tracks": ts, "measures": len(self.song.measureHeaders), "tempo": self.song.tempo}
    
    # =========================================================================
    # INTERNAL
    # =========================================================================
    
    def _set_track_tuning(self, track: Track, tuning: str):
        if tuning not in TUNINGS:
            tuning = "standard"
        mv = TUNINGS[tuning]
        track.strings = [GuitarString(number=i + 1, value=v) for i, v in enumerate(reversed(mv))]
    
    def _set_tuning_from_midi(self, track: Track, midi_values: List[int]):
        """Set tuning from list of MIDI values (GP8 format: high to low)."""
        track.strings = [GuitarString(number=i + 1, value=v) for i, v in enumerate(midi_values)]
    
    def _get_tuning_name(self, track: Track) -> str:
        if not track.strings:
            return "unknown"
        vals = [s.value for s in sorted(track.strings, key=lambda s: -s.number)]
        for name, preset in TUNINGS.items():
            if vals == preset:
                return name
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
    
    def _note_name(self, midi_value: int) -> str:
        return NOTE_NAMES[midi_value % 12]


_controller: Optional[GuitarProController] = None

def get_controller() -> GuitarProController:
    global _controller
    if _controller is None:
        _controller = GuitarProController()
    return _controller