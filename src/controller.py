"""
Guitar Pro Controller v2.2
FIXES: NoteEffect init, Beat.start, Duration handling, dead note type
"""

import logging
import re
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


class GuitarProController:
    """Guitar Pro Controller v2.2"""
    
    def __init__(self):
        self.song: Optional[Song] = None
        self._clipboard: List[Dict] = []
    
    def load(self, path: str) -> Dict[str, Any]:
        self.song = parse(path)
        return self.get_info()
    
    def save(self, path: str) -> bool:
        if not self.song:
            raise ValueError("No song loaded")
        write(self.song, path, version=(5, 1, 0))
        return True
    
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
    
    def add_track(self, name: str, tuning: str = "standard", instrument: int = 25) -> int:
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
    
    def add_note(self, track: int, measure: int, beat: int, 
                 string: int, fret: int, duration: int = 4) -> bool:
        return self.add_notes_batch([{
            "track": track, "measure": measure, "beat": beat,
            "string": string, "fret": fret, "duration": duration
        }])
    
    def add_notes_batch(self, notes: List[Dict]) -> bool:
        """Add multiple notes - THE CORE FUNCTION"""
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
            
            # Create beats up to the needed index
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
                
                # IMPORTANT: Initialize effect properly
                if note.effect is None:
                    note.effect = NoteEffect()
                
                if n.get("palm_mute"):
                    note.effect.palmMute = True
                if n.get("hammer_on") or n.get("pull_off"):
                    note.effect.hammer = True
                if n.get("slide"):
                    note.effect.slides = [gp.SlideType.shiftSlideTo]
                if n.get("vibrato"):
                    note.effect.vibrato = True
                if n.get("ghost"):
                    note.effect.ghostNote = True
                if n.get("dead"):
                    note.type = gp.NoteType.dead
                if n.get("let_ring"):
                    note.effect.letRing = True
                
                beat.notes.append(note)
        
        return True
    
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
        
        max_len = max(len(c) for _, c in tab_lines)
        current_measure, current_beat = start_measure, 0
        beats_per_measure = 8 if duration == 8 else 4
        col = 0
        
        while col < max_len:
            is_bar = all(col < len(c) and c[col] == '|' for _, c in tab_lines)
            if is_bar:
                col += 1
                continue
            
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
                        "track": track, "measure": current_measure, "beat": current_beat,
                        "string": string_num, "fret": int(fret_str), "duration": duration
                    })
            
            if column_notes:
                notes.extend(column_notes)
                current_beat += 1
                if current_beat >= beats_per_measure:
                    current_beat = 0
                    current_measure += 1
            
            col += max_fret_len
            while col < max_len and not any(
                col < len(c) and (c[col].isdigit() or c[col] == '|') for _, c in tab_lines
            ):
                col += 1
        
        return notes
    
    def _parse_compact_tab(self, tab: str, track: int, start_measure: int, duration: int) -> List[Dict]:
        notes = []
        current_beat, current_measure = 0, start_measure
        beats_per_measure = 8 if duration == 8 else 4
        
        for part in tab.strip().split():
            if ':' in part:
                string_str, frets_str = part.split(':', 1)
                string = int(string_str)
                for fret_str in frets_str.split('-'):
                    fret_str = fret_str.strip()
                    if fret_str.lstrip('-').isdigit() or fret_str == '0':
                        notes.append({
                            "track": track, "measure": current_measure, "beat": current_beat,
                            "string": string, "fret": int(fret_str), "duration": duration
                        })
                        current_beat += 1
                        if current_beat >= beats_per_measure:
                            current_beat = 0
                            current_measure += 1
        return notes
    
    def _count_measures(self, notes: List[Dict]) -> int:
        return max((n.get("measure", 0) for n in notes), default=-1) + 1 if notes else 0
    
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
                        note_data = {
                            "measure": m_idx - start_measure, "beat": b_idx,
                            "string": note.string, "fret": note.value,
                            "duration": beat.duration.value if beat.duration else 4,
                        }
                        if note.effect and note.effect.palmMute:
                            note_data["palm_mute"] = True
                        if note.effect and note.effect.hammer:
                            note_data["hammer_on"] = True
                        self._clipboard.append(note_data)
        return {"notes_copied": len(self._clipboard), "measures": end_measure - start_measure + 1}
    
    def paste_measures(self, track_index: int, start_measure: int, repeat: int = 1) -> Dict[str, Any]:
        if not self._clipboard:
            return {"error": "Clipboard empty"}
        if not self.song:
            self.create()
        pattern_measures = max(n["measure"] for n in self._clipboard) + 1
        notes_to_add = []
        for rep in range(repeat):
            offset = rep * pattern_measures
            for note in self._clipboard:
                notes_to_add.append({**note, "track": track_index,
                                     "measure": start_measure + note["measure"] + offset})
        total_needed = start_measure + (pattern_measures * repeat)
        while len(self.song.measureHeaders) < total_needed:
            self._add_measure_header()
        self.add_notes_batch(notes_to_add)
        return {"notes_added": len(notes_to_add), "measures_filled": pattern_measures * repeat}
    
    def repeat_pattern(self, track_index: int, source_start: int, source_end: int,
                       dest_start: int, times: int = 1) -> Dict[str, Any]:
        self.copy_measures(track_index, source_start, source_end)
        return self.paste_measures(track_index, dest_start, times)
    
    def copy_track_from_file(self, source_path: str, source_track_index: int,
                             dest_track_name: str = None, start_measure: int = 0, 
                             end_measure: int = None) -> Dict[str, Any]:
        if not self.song:
            self.create()
        source_song = parse(source_path)
        if source_track_index >= len(source_song.tracks):
            return {"error": f"Source track {source_track_index} not found"}
        source_track = source_song.tracks[source_track_index]
        if end_measure is None:
            end_measure = len(source_track.measures) - 1
        track_name = dest_track_name or source_track.name
        new_track_idx = self.add_track(track_name, self._get_tuning_name(source_track),
                                       source_track.channel.instrument)
        new_track = self.song.tracks[new_track_idx]
        new_track.strings = [GuitarString(number=s.number, value=s.value) for s in source_track.strings]
        measures_needed = end_measure - start_measure + 1
        while len(self.song.measureHeaders) < measures_needed:
            self._add_measure_header()
        notes_to_add = []
        for m_idx in range(start_measure, min(end_measure + 1, len(source_track.measures))):
            for v_idx, voice in enumerate(source_track.measures[m_idx].voices):
                for b_idx, beat in enumerate(voice.beats):
                    for note in beat.notes:
                        note_data = {
                            "track": new_track_idx, "measure": m_idx - start_measure,
                            "beat": b_idx, "voice": v_idx, "string": note.string, "fret": note.value,
                            "duration": beat.duration.value if beat.duration else 4,
                        }
                        if note.effect:
                            if note.effect.palmMute: note_data["palm_mute"] = True
                            if note.effect.hammer: note_data["hammer_on"] = True
                            if note.effect.vibrato: note_data["vibrato"] = True
                        notes_to_add.append(note_data)
        if notes_to_add:
            self.add_notes_batch(notes_to_add)
        return {"track_name": track_name, "track_index": new_track_idx,
                "notes_copied": len(notes_to_add), "measures_copied": measures_needed}
    
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
        current_measure, current_beat, chords_added = start_measure, 0, 0
        for chord_name in chords:
            if chord_name in CHORDS:
                while current_measure >= len(self.song.measureHeaders):
                    self._add_measure_header()
                self.add_chord_by_name(track, current_measure, current_beat, chord_name, duration)
                chords_added += 1
            current_beat += beats_per_chord
            while current_beat >= 4:
                current_beat -= 4
                current_measure += 1
        return {"chords_added": chords_added}
    
    def list_chords(self) -> List[str]:
        return list(CHORDS.keys())
    
    def list_riff_templates(self) -> Dict[str, str]:
        return {name: t["description"] for name, t in RIFF_TEMPLATES.items()}
    
    def add_riff_template(self, track: int, measure: int, template_name: str,
                          root_fret: int = 0, repeat: int = 1) -> Dict[str, Any]:
        if template_name not in RIFF_TEMPLATES:
            return {"error": f"Unknown template: {template_name}"}
        template = RIFF_TEMPLATES[template_name]
        while len(self.song.measureHeaders) < measure + repeat:
            self._add_measure_header()
        notes_to_add = []
        for rep in range(repeat):
            for nt in template["pattern"]:
                notes_to_add.append({
                    "track": track, "measure": measure + rep, "beat": nt["beat"],
                    "string": nt["string"], "fret": nt["fret"] + root_fret,
                    "duration": template["duration"], "palm_mute": nt.get("palm_mute", False)
                })
        self.add_notes_batch(notes_to_add)
        return {"notes_added": len(notes_to_add), "measures": repeat}
    
    def add_notes_multi_track(self, notes_by_track: Dict[int, List[Dict]]) -> Dict[str, Any]:
        all_notes = [{**n, "track": t} for t, notes in notes_by_track.items() for n in notes]
        self.add_notes_batch(all_notes)
        return {"total_notes_added": len(all_notes), "tracks_modified": len(notes_by_track)}
    
    def transpose_track(self, track_index: int, semitones: int,
                        start_measure: int = 0, end_measure: int = None) -> Dict[str, Any]:
        if not self.song or track_index >= len(self.song.tracks):
            return {"error": "Invalid track"}
        track = self.song.tracks[track_index]
        if end_measure is None:
            end_measure = len(track.measures) - 1
        notes_transposed = 0
        for m_idx in range(start_measure, min(end_measure + 1, len(track.measures))):
            for voice in track.measures[m_idx].voices:
                for beat in voice.beats:
                    for note in beat.notes:
                        new_fret = note.value + semitones
                        if 0 <= new_fret <= 24:
                            note.value = new_fret
                            notes_transposed += 1
        return {"notes_transposed": notes_transposed}
    
    def transpose_section(self, track_index: int, start_measure: int, 
                          end_measure: int, semitones: int) -> Dict[str, Any]:
        return self.transpose_track(track_index, semitones, start_measure, end_measure)
    
    def add_palm_muted_notes(self, track: int, measure: int, string: int,
                             frets: List[int], start_beat: int = 0, duration: int = 8) -> bool:
        return self.add_notes_batch([
            {"track": track, "measure": measure, "beat": start_beat + i,
             "string": string, "fret": fret, "duration": duration, "palm_mute": True}
            for i, fret in enumerate(frets)
        ])
    
    def get_tab(self, track_index: int, start_measure: int = 0, end_measure: int = None) -> str:
        if not self.song or track_index >= len(self.song.tracks):
            return "Invalid track"
        track = self.song.tracks[track_index]
        num_strings = len(track.strings)
        if end_measure is None:
            end_measure = len(track.measures)
        string_names = [self._note_name(s.value) for s in sorted(track.strings, key=lambda s: s.number)]
        tab_lines = [f"{name}|" for name in string_names]
        for m_idx in range(start_measure, min(end_measure, len(track.measures))):
            measure = track.measures[m_idx]
            beat_data = [{note.string: note.value for note in beat.notes}
                         for voice in measure.voices for beat in voice.beats] or [{}]
            for notes_dict in beat_data:
                for string_num in range(1, num_strings + 1):
                    line_idx = num_strings - string_num
                    if string_num in notes_dict:
                        tab_lines[line_idx] += str(notes_dict[string_num]).ljust(3, '-')
                    else:
                        tab_lines[line_idx] += "---"
            for i in range(num_strings):
                tab_lines[i] += "|"
        return '\n'.join(tab_lines)
    
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
        track_stats = []
        total_notes = 0
        for i, track in enumerate(self.song.tracks):
            track_notes = sum(len(beat.notes) for m in track.measures for v in m.voices for beat in v.beats)
            total_notes += track_notes
            track_stats.append({"name": track.name, "notes": track_notes, "measures": len(track.measures)})
        return {"title": self.song.title, "total_notes": total_notes,
                "tracks": track_stats, "measures": len(self.song.measureHeaders), "tempo": self.song.tempo}
    
    def _set_track_tuning(self, track: Track, tuning: str):
        if tuning not in TUNINGS:
            tuning = "standard"
        midi_values = TUNINGS[tuning]
        track.strings = [GuitarString(number=i + 1, value=v) for i, v in enumerate(reversed(midi_values))]
    
    def _get_tuning_name(self, track: Track) -> str:
        if not track.strings:
            return "unknown"
        values = [s.value for s in sorted(track.strings, key=lambda s: -s.number)]
        for name, preset in TUNINGS.items():
            if values == preset:
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