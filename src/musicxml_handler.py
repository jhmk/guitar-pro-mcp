"""
MusicXML Import/Export Handler for Guitar Pro MCP v3.0

Supports:
- Import MusicXML (.xml, .musicxml) -> PyGuitarPro Song
- Export PyGuitarPro Song -> MusicXML

Note: MusicXML doesn't have native tablature support, so we convert
pitch information to fret positions based on tuning.
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# MIDI note to pitch mapping
PITCH_NAMES = ['C', 'C', 'D', 'D', 'E', 'F', 'F', 'G', 'G', 'A', 'A', 'B']
PITCH_ALTERS = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]  # 0=natural, 1=sharp

# Duration mapping (GP value to MusicXML type)
DURATION_TO_TYPE = {
    1: 'whole',
    2: 'half', 
    4: 'quarter',
    8: 'eighth',
    16: '16th',
    32: '32nd',
    64: '64th'
}

TYPE_TO_DURATION = {v: k for k, v in DURATION_TO_TYPE.items()}

# Standard tuning MIDI values (low to high: E2 A2 D3 G3 B3 E4)
STANDARD_TUNING = [40, 45, 50, 55, 59, 64]


class MusicXMLExporter:
    """Export PyGuitarPro Song to MusicXML format."""
    
    def __init__(self):
        self.divisions = 960  # Ticks per quarter note
    
    def export(self, song, path: str):
        """Export song to MusicXML file."""
        root = self._build_xml(song)
        
        # Pretty print
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        # Remove extra blank lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _build_xml(self, song) -> ET.Element:
        """Build MusicXML tree from song."""
        root = ET.Element('score-partwise', version="4.0")
        
        # Work info
        work = ET.SubElement(root, 'work')
        ET.SubElement(work, 'work-title').text = song.title or "Untitled"
        
        # Identification
        ident = ET.SubElement(root, 'identification')
        if song.artist:
            creator = ET.SubElement(ident, 'creator', type="composer")
            creator.text = song.artist
        
        encoding = ET.SubElement(ident, 'encoding')
        ET.SubElement(encoding, 'software').text = "Guitar Pro MCP v3.0"
        ET.SubElement(encoding, 'encoding-date').text = datetime.now().strftime('%Y-%m-%d')
        
        # Part list
        part_list = ET.SubElement(root, 'part-list')
        for i, track in enumerate(song.tracks):
            score_part = ET.SubElement(part_list, 'score-part', id=f"P{i+1}")
            ET.SubElement(score_part, 'part-name').text = track.name
            
            # MIDI instrument info
            midi_inst = ET.SubElement(score_part, 'midi-instrument', id=f"P{i+1}-I1")
            ET.SubElement(midi_inst, 'midi-channel').text = str(i + 1)
            ET.SubElement(midi_inst, 'midi-program').text = str(track.channel.instrument + 1)
        
        # Parts
        for i, track in enumerate(song.tracks):
            part = ET.SubElement(root, 'part', id=f"P{i+1}")
            self._build_part(part, track, song)
        
        return root
    
    def _build_part(self, part_elem: ET.Element, track, song):
        """Build part element from track."""
        # Get tuning for fret-to-pitch conversion
        tuning = [s.value for s in sorted(track.strings, key=lambda s: s.number)]
        
        for m_idx, measure in enumerate(track.measures):
            measure_elem = ET.SubElement(part_elem, 'measure', number=str(m_idx + 1))
            
            # Attributes (first measure or when time signature changes)
            if m_idx == 0:
                attrs = ET.SubElement(measure_elem, 'attributes')
                ET.SubElement(attrs, 'divisions').text = str(self.divisions)
                
                # Key signature (C major for simplicity)
                key = ET.SubElement(attrs, 'key')
                ET.SubElement(key, 'fifths').text = '0'
                
                # Time signature
                header = song.measureHeaders[m_idx] if m_idx < len(song.measureHeaders) else None
                if header and header.timeSignature:
                    time = ET.SubElement(attrs, 'time')
                    ET.SubElement(time, 'beats').text = str(header.timeSignature.numerator)
                    ET.SubElement(time, 'beat-type').text = str(header.timeSignature.denominator.value)
                
                # Clef (treble with 8vb for guitar)
                clef = ET.SubElement(attrs, 'clef')
                ET.SubElement(clef, 'sign').text = 'G'
                ET.SubElement(clef, 'line').text = '2'
                ET.SubElement(clef, 'clef-octave-change').text = '-1'
                
                # Staff details for TAB
                staff_details = ET.SubElement(attrs, 'staff-details')
                ET.SubElement(staff_details, 'staff-lines').text = str(len(track.strings))
                for string in sorted(track.strings, key=lambda s: s.number):
                    staff_tuning = ET.SubElement(staff_details, 'staff-tuning', line=str(string.number))
                    pitch_name, alter, octave = self._midi_to_pitch(string.value)
                    ET.SubElement(staff_tuning, 'tuning-step').text = pitch_name
                    if alter != 0:
                        ET.SubElement(staff_tuning, 'tuning-alter').text = str(alter)
                    ET.SubElement(staff_tuning, 'tuning-octave').text = str(octave)
            
            # Direction (tempo) - first measure only
            if m_idx == 0 and song.tempo:
                direction = ET.SubElement(measure_elem, 'direction', placement="above")
                direction_type = ET.SubElement(direction, 'direction-type')
                metronome = ET.SubElement(direction_type, 'metronome')
                ET.SubElement(metronome, 'beat-unit').text = 'quarter'
                ET.SubElement(metronome, 'per-minute').text = str(song.tempo)
                sound = ET.SubElement(direction, 'sound', tempo=str(song.tempo))
            
            # Notes
            for voice in measure.voices:
                for beat in voice.beats:
                    if not beat.notes:
                        # Rest
                        note_elem = ET.SubElement(measure_elem, 'note')
                        ET.SubElement(note_elem, 'rest')
                        duration = self._gp_duration_to_divisions(beat.duration.value if beat.duration else 4)
                        ET.SubElement(note_elem, 'duration').text = str(duration)
                        ET.SubElement(note_elem, 'type').text = DURATION_TO_TYPE.get(
                            beat.duration.value if beat.duration else 4, 'quarter')
                    else:
                        # Notes (chord if multiple)
                        is_chord = len(beat.notes) > 1
                        for n_idx, note in enumerate(beat.notes):
                            note_elem = ET.SubElement(measure_elem, 'note')
                            
                            # Chord indicator (not for first note)
                            if n_idx > 0:
                                ET.SubElement(note_elem, 'chord')
                            
                            # Pitch from fret + string
                            midi_note = self._fret_to_midi(note.value, note.string, tuning)
                            pitch_name, alter, octave = self._midi_to_pitch(midi_note)
                            
                            pitch = ET.SubElement(note_elem, 'pitch')
                            ET.SubElement(pitch, 'step').text = pitch_name
                            if alter != 0:
                                ET.SubElement(pitch, 'alter').text = str(alter)
                            ET.SubElement(pitch, 'octave').text = str(octave)
                            
                            # Duration
                            dur_val = beat.duration.value if beat.duration else 4
                            duration = self._gp_duration_to_divisions(dur_val)
                            ET.SubElement(note_elem, 'duration').text = str(duration)
                            ET.SubElement(note_elem, 'type').text = DURATION_TO_TYPE.get(dur_val, 'quarter')
                            
                            # Technical (string/fret for TAB)
                            notations = ET.SubElement(note_elem, 'notations')
                            technical = ET.SubElement(notations, 'technical')
                            ET.SubElement(technical, 'string').text = str(note.string)
                            ET.SubElement(technical, 'fret').text = str(note.value)
                            
                            # Articulations
                            if note.effect:
                                articulations = ET.SubElement(notations, 'articulations')
                                if note.effect.staccato:
                                    ET.SubElement(articulations, 'staccato')
                                if note.effect.accentuatedNote:
                                    ET.SubElement(articulations, 'accent')
                                if note.effect.heavyAccentuatedNote:
                                    ET.SubElement(articulations, 'strong-accent')
                            
                            # Other effects as ornaments
                            if note.effect:
                                if note.effect.vibrato:
                                    ornaments = notations.find('ornaments')
                                    if ornaments is None:
                                        ornaments = ET.SubElement(notations, 'ornaments')
                                    ET.SubElement(ornaments, 'wavy-line', type="start")
                                
                                if note.effect.trill:
                                    ornaments = notations.find('ornaments')
                                    if ornaments is None:
                                        ornaments = ET.SubElement(notations, 'ornaments')
                                    ET.SubElement(ornaments, 'trill-mark')
                                
                                if note.effect.hammer:
                                    ET.SubElement(technical, 'hammer-on', type="start")
                                
                                if note.effect.palmMute:
                                    # No direct MusicXML equivalent, use text
                                    pass
    
    def _midi_to_pitch(self, midi: int) -> Tuple[str, int, int]:
        """Convert MIDI note to (step, alter, octave)."""
        octave = (midi // 12) - 1
        note_idx = midi % 12
        step = PITCH_NAMES[note_idx]
        alter = PITCH_ALTERS[note_idx]
        return step, alter, octave
    
    def _fret_to_midi(self, fret: int, string: int, tuning: List[int]) -> int:
        """Convert fret/string to MIDI note."""
        # String numbers are 1-based, tuning list is 0-based (high to low)
        string_idx = string - 1
        if string_idx < len(tuning):
            open_note = tuning[string_idx]
            return open_note + fret
        return 60  # Default to middle C
    
    def _gp_duration_to_divisions(self, gp_duration: int) -> int:
        """Convert GP duration value to MusicXML divisions."""
        # GP: 1=whole, 2=half, 4=quarter, 8=eighth, etc.
        # divisions=960 means quarter note = 960
        quarter_divisions = self.divisions
        return (4 * quarter_divisions) // gp_duration


class MusicXMLImporter:
    """Import MusicXML file to note list for PyGuitarPro."""
    
    def __init__(self):
        self.divisions = 1  # Will be read from file
    
    def import_file(self, path: str) -> Dict[str, Any]:
        """
        Import MusicXML file.
        
        Returns dict with:
            - title, artist, tempo
            - tracks: [{name, instrument, tuning, notes: [...]}]
        """
        tree = ET.parse(path)
        root = tree.getroot()
        
        # Handle namespace if present
        ns = ''
        if root.tag.startswith('{'):
            ns = root.tag.split('}')[0] + '}'
        
        result = {
            "title": "",
            "artist": "",
            "tempo": 120,
            "time_signature": (4, 4),
            "tracks": []
        }
        
        # Work title
        work_title = root.find(f'.//{ns}work-title')
        if work_title is not None and work_title.text:
            result["title"] = work_title.text
        
        # Creator/composer
        creator = root.find(f'.//{ns}creator[@type="composer"]')
        if creator is not None and creator.text:
            result["artist"] = creator.text
        
        # Parts
        parts = root.findall(f'.//{ns}part')
        part_list = root.find(f'.//{ns}part-list')
        
        for part_idx, part in enumerate(parts):
            part_id = part.get('id', f'P{part_idx+1}')
            
            # Get part name
            part_name = "Track"
            if part_list is not None:
                score_part = part_list.find(f'.//{ns}score-part[@id="{part_id}"]')
                if score_part is not None:
                    name_elem = score_part.find(f'.//{ns}part-name')
                    if name_elem is not None and name_elem.text:
                        part_name = name_elem.text
            
            track_data = {
                "name": part_name,
                "instrument": 25,  # Default guitar
                "tuning": STANDARD_TUNING.copy(),
                "notes": []
            }
            
            # Get MIDI program
            if part_list is not None:
                midi_prog = part_list.find(f'.//{ns}score-part[@id="{part_id}"]//{ns}midi-program')
                if midi_prog is not None and midi_prog.text:
                    track_data["instrument"] = int(midi_prog.text) - 1
            
            # Parse measures
            current_time = 0
            measure_num = 0
            
            for measure in part.findall(f'{ns}measure'):
                measure_num += 1
                beat_in_measure = 0
                
                # Get divisions
                divisions_elem = measure.find(f'.//{ns}divisions')
                if divisions_elem is not None and divisions_elem.text:
                    self.divisions = int(divisions_elem.text)
                
                # Get tempo
                tempo_elem = measure.find(f'.//{ns}sound[@tempo]')
                if tempo_elem is not None:
                    result["tempo"] = int(float(tempo_elem.get('tempo', 120)))
                
                # Get time signature
                time_elem = measure.find(f'.//{ns}time')
                if time_elem is not None:
                    beats = time_elem.find(f'{ns}beats')
                    beat_type = time_elem.find(f'{ns}beat-type')
                    if beats is not None and beat_type is not None:
                        result["time_signature"] = (int(beats.text), int(beat_type.text))
                
                # Get tuning from staff-details
                staff_tunings = measure.findall(f'.//{ns}staff-tuning')
                if staff_tunings:
                    new_tuning = []
                    for st in staff_tunings:
                        step = st.find(f'{ns}tuning-step')
                        octave = st.find(f'{ns}tuning-octave')
                        alter = st.find(f'{ns}tuning-alter')
                        if step is not None and octave is not None:
                            midi = self._pitch_to_midi(
                                step.text,
                                int(alter.text) if alter is not None else 0,
                                int(octave.text)
                            )
                            new_tuning.append(midi)
                    if new_tuning:
                        track_data["tuning"] = new_tuning
                
                # Parse notes
                chord_notes = []
                
                for elem in measure:
                    if elem.tag == f'{ns}note' or elem.tag == 'note':
                        is_chord = elem.find(f'{ns}chord') is not None or elem.find('chord') is not None
                        is_rest = elem.find(f'{ns}rest') is not None or elem.find('rest') is not None
                        
                        # Get duration
                        dur_elem = elem.find(f'{ns}duration') or elem.find('duration')
                        duration_divs = int(dur_elem.text) if dur_elem is not None else self.divisions
                        gp_duration = self._divisions_to_gp_duration(duration_divs)
                        
                        if is_rest:
                            if not is_chord:
                                beat_in_measure += 1
                            continue
                        
                        # Get pitch
                        pitch_elem = elem.find(f'{ns}pitch') or elem.find('pitch')
                        if pitch_elem is None:
                            continue
                        
                        step = pitch_elem.find(f'{ns}step') or pitch_elem.find('step')
                        octave = pitch_elem.find(f'{ns}octave') or pitch_elem.find('octave')
                        alter_elem = pitch_elem.find(f'{ns}alter') or pitch_elem.find('alter')
                        
                        if step is None or octave is None:
                            continue
                        
                        alter = int(alter_elem.text) if alter_elem is not None else 0
                        midi_note = self._pitch_to_midi(step.text, alter, int(octave.text))
                        
                        # Get string/fret if available (from technical)
                        string_elem = elem.find(f'.//{ns}string') or elem.find('.//string')
                        fret_elem = elem.find(f'.//{ns}fret') or elem.find('.//fret')
                        
                        if string_elem is not None and fret_elem is not None:
                            string = int(string_elem.text)
                            fret = int(fret_elem.text)
                        else:
                            # Calculate string/fret from MIDI note
                            string, fret = self._midi_to_fret(midi_note, track_data["tuning"])
                        
                        note_data = {
                            "track": part_idx,
                            "measure": measure_num - 1,
                            "beat": beat_in_measure,
                            "string": string,
                            "fret": fret,
                            "duration": gp_duration
                        }
                        
                        # Check for effects
                        if elem.find(f'.//{ns}staccato') is not None or elem.find('.//staccato') is not None:
                            note_data["staccato"] = True
                        if elem.find(f'.//{ns}accent') is not None or elem.find('.//accent') is not None:
                            note_data["accent"] = True
                        if elem.find(f'.//{ns}trill-mark') is not None or elem.find('.//trill-mark') is not None:
                            note_data["trill"] = True
                        if elem.find(f'.//{ns}hammer-on') is not None or elem.find('.//hammer-on') is not None:
                            note_data["hammer_on"] = True
                        
                        track_data["notes"].append(note_data)
                        
                        if not is_chord:
                            beat_in_measure += 1
                
            result["tracks"].append(track_data)
        
        return result
    
    def _pitch_to_midi(self, step: str, alter: int, octave: int) -> int:
        """Convert pitch name to MIDI note."""
        step_map = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
        return (octave + 1) * 12 + step_map.get(step.upper(), 0) + alter
    
    def _midi_to_fret(self, midi: int, tuning: List[int]) -> Tuple[int, int]:
        """Find best string/fret for a MIDI note."""
        best_string = 1
        best_fret = 0
        best_diff = 999
        
        for i, open_note in enumerate(tuning):
            fret = midi - open_note
            if 0 <= fret <= 24:
                # Prefer lower frets
                if fret < best_diff:
                    best_diff = fret
                    best_string = i + 1
                    best_fret = fret
        
        return best_string, best_fret
    
    def _divisions_to_gp_duration(self, divisions: int) -> int:
        """Convert MusicXML divisions to GP duration."""
        if self.divisions == 0:
            return 4
        
        # Calculate how many quarter notes
        quarters = divisions / self.divisions
        
        if quarters >= 4:
            return 1  # whole
        elif quarters >= 2:
            return 2  # half
        elif quarters >= 1:
            return 4  # quarter
        elif quarters >= 0.5:
            return 8  # eighth
        elif quarters >= 0.25:
            return 16  # sixteenth
        else:
            return 32  # thirty-second


def export_musicxml(song, path: str):
    """Export PyGuitarPro song to MusicXML."""
    exporter = MusicXMLExporter()
    exporter.export(song, path)


def import_musicxml(path: str) -> Dict[str, Any]:
    """Import MusicXML file."""
    importer = MusicXMLImporter()
    return importer.import_file(path)
