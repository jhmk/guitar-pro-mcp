"""
Guitar Pro MCP Tools v3.0
All tool definitions for the MCP server.
"""

from mcp.server.fastmcp import FastMCP
from typing import Dict, List, Any, Optional
from .controller import get_controller

mcp = FastMCP("Guitar Pro MCP Server v3.0")


# =============================================================================
# FILE OPERATIONS
# =============================================================================

@mcp.tool()
def gp_load(file_path: str) -> Dict[str, Any]:
    """Load a Guitar Pro file (GP3/4/5/7/8) or MusicXML."""
    return get_controller().load(file_path)

@mcp.tool()
def gp_save(file_path: str) -> Dict[str, Any]:
    """Save to Guitar Pro 5 (.gp5) or MusicXML (.xml/.musicxml)."""
    return {"success": get_controller().save(file_path)}

@mcp.tool()
def gp_export_musicxml(file_path: str) -> Dict[str, Any]:
    """Export current song to MusicXML format."""
    return {"success": get_controller().export_musicxml(file_path)}


# =============================================================================
# SONG OPERATIONS
# =============================================================================

@mcp.tool()
def gp_create(title: str = "New Song", artist: str = "", tempo: int = 120,
              tuning: str = "standard") -> Dict[str, Any]:
    """Create a new Guitar Pro song."""
    return get_controller().create(title, artist, tempo, tuning)

@mcp.tool()
def gp_create_complete(title: str, artist: str = "", tempo: int = 120,
                       tracks: List[Dict] = None, measures: int = 4,
                       notes: List[Dict] = None) -> Dict[str, Any]:
    """Create a complete song with tracks and notes in one call."""
    return get_controller().create_complete(title, artist, tempo, tracks, measures, notes)

@mcp.tool()
def gp_info() -> Dict[str, Any]:
    """Get current song info."""
    return get_controller().get_info()

@mcp.tool()
def gp_set_properties(title: str = None, artist: str = None, 
                      album: str = None, tempo: int = None) -> Dict[str, Any]:
    """Update song properties."""
    return {"success": get_controller().set_properties(title, artist, album, tempo)}


# =============================================================================
# TRACK OPERATIONS
# =============================================================================

@mcp.tool()
def gp_add_track(name: str, tuning: str = "standard", instrument: int = 25) -> Dict[str, Any]:
    """Add a new track. Instrument: 25=overdriven guitar, 29=distortion, 33=bass."""
    return {"track_index": get_controller().add_track(name, tuning, instrument)}

@mcp.tool()
def gp_set_tuning(track_index: int, tuning: str) -> Dict[str, Any]:
    """Set track tuning. Options: standard, drop_d, drop_c, etc."""
    return {"success": get_controller().set_track_tuning(track_index, tuning)}

@mcp.tool()
def gp_get_tracks() -> Dict[str, Any]:
    """Get all tracks info."""
    return {"tracks": get_controller().get_tracks()}


# =============================================================================
# MEASURE OPERATIONS
# =============================================================================

@mcp.tool()
def gp_add_measures(count: int = 1) -> Dict[str, Any]:
    """Add empty measures."""
    return {"total_measures": get_controller().add_measures(count)}

@mcp.tool()
def gp_set_time_signature(measure: int, numerator: int, denominator: int) -> Dict[str, Any]:
    """Set time signature for a measure."""
    return {"success": get_controller().set_time_signature(measure, numerator, denominator)}


# =============================================================================
# NOTE OPERATIONS
# =============================================================================

@mcp.tool()
def gp_add_note(track: int, measure: int, beat: int, string: int, fret: int,
                duration: int = 4) -> Dict[str, Any]:
    """Add a single note."""
    return {"success": get_controller().add_note(track, measure, beat, string, fret, duration)}

@mcp.tool()
def gp_add_notes_batch(notes: List[Dict]) -> Dict[str, Any]:
    """
    Add multiple notes with effects.
    
    Each note dict can have:
        track, measure, beat, string, fret, duration,
        palm_mute, hammer_on, slide, vibrato, ghost, dead, let_ring,
        staccato, accent, bend ("half"/"full"), harmonic ("natural"/"pinch"),
        trill (fret), tremolo_picking (8/16/32), grace_fret
    """
    return {"success": get_controller().add_notes_batch(notes)}

@mcp.tool()
def gp_add_notes_multi_track(notes_by_track: Dict[int, List[Dict]]) -> Dict[str, Any]:
    """Add notes to multiple tracks at once."""
    return get_controller().add_notes_multi_track(notes_by_track)


# =============================================================================
# EFFECT SHORTCUTS
# =============================================================================

@mcp.tool()
def gp_add_bend(track: int, measure: int, beat: int, string: int, fret: int,
                bend_type: str = "full", release: bool = False, duration: int = 4) -> Dict[str, Any]:
    """Add a note with bend. bend_type: 'half', 'full', 'full_half', 'double'"""
    return {"success": get_controller().add_bend(track, measure, beat, string, fret, 
                                                  bend_type, release, duration)}

@mcp.tool()
def gp_add_harmonic(track: int, measure: int, beat: int, string: int, fret: int,
                    harmonic_type: str = "natural", duration: int = 4) -> Dict[str, Any]:
    """Add harmonic. Type: 'natural', 'artificial', 'pinch', 'tap'"""
    return {"success": get_controller().add_harmonic(track, measure, beat, string, fret,
                                                      harmonic_type, duration)}

@mcp.tool()
def gp_add_trill(track: int, measure: int, beat: int, string: int, fret: int,
                 trill_fret: int, speed: int = 16, duration: int = 4) -> Dict[str, Any]:
    """Add trill between fret and trill_fret. Speed: 8, 16, 32"""
    return {"success": get_controller().add_trill(track, measure, beat, string, fret,
                                                   trill_fret, speed, duration)}

@mcp.tool()
def gp_add_tremolo(track: int, measure: int, beat: int, string: int, fret: int,
                   speed: int = 16, duration: int = 4) -> Dict[str, Any]:
    """Add tremolo picked note. Speed: 8, 16, 32"""
    return {"success": get_controller().add_tremolo_picking(track, measure, beat, string, fret,
                                                             speed, duration)}

@mcp.tool()
def gp_add_grace_note(track: int, measure: int, beat: int, string: int, fret: int,
                      grace_fret: int, transition: str = "hammer", duration: int = 4) -> Dict[str, Any]:
    """Add note with grace note. Transition: 'none', 'slide', 'bend', 'hammer'"""
    return {"success": get_controller().add_grace_note(track, measure, beat, string, fret,
                                                        grace_fret, transition, duration)}


# =============================================================================
# CHORDS
# =============================================================================

@mcp.tool()
def gp_add_chord(track: int, measure: int, beat: int, chord_name: str = None,
                 frets: List[int] = None, duration: int = 4) -> Dict[str, Any]:
    """Add chord by name (E, Am, G5, etc.) or frets list."""
    ctrl = get_controller()
    if chord_name:
        return {"success": ctrl.add_chord_by_name(track, measure, beat, chord_name, duration)}
    elif frets:
        return {"success": ctrl.add_chord(track, measure, beat, frets, duration)}
    return {"error": "Provide chord_name or frets"}

@mcp.tool()
def gp_add_power_chord(track: int, measure: int, beat: int, root_string: int,
                       root_fret: int, duration: int = 4) -> Dict[str, Any]:
    """Add power chord (root + 5th + octave)."""
    return {"success": get_controller().add_power_chord(track, measure, beat, root_string, 
                                                         root_fret, duration)}

@mcp.tool()
def gp_add_chord_progression(track: int, start_measure: int, chords: List[str],
                             beats_per_chord: int = 4, duration: int = 4) -> Dict[str, Any]:
    """Add chord progression like ["E", "A", "B", "E"]."""
    return get_controller().add_chord_progression(track, start_measure, chords, 
                                                   beats_per_chord, duration)


# =============================================================================
# TAB & TEMPLATES
# =============================================================================

@mcp.tool()
def gp_import_tab(tab: str, track: int = 0, start_measure: int = 0, 
                  duration: int = 8) -> Dict[str, Any]:
    """
    Import ASCII tab.
    
    Standard format:
        e|--0--3--|
        B|--1--0--|
        ...
    
    Compact format:
        6:0-0-3-5 5:2-2-5-7
    """
    return get_controller().import_tab_bulk(tab, track, start_measure, duration)

@mcp.tool()
def gp_add_riff_template(track: int, measure: int, template_name: str,
                         root_fret: int = 0, repeat: int = 1) -> Dict[str, Any]:
    """Add riff template. Use gp_list_templates() to see options."""
    return get_controller().add_riff_template(track, measure, template_name, root_fret, repeat)

@mcp.tool()
def gp_add_palm_mutes(track: int, measure: int, string: int, frets: List[int],
                      start_beat: int = 0, duration: int = 8) -> Dict[str, Any]:
    """Add sequence of palm-muted notes."""
    return {"success": get_controller().add_palm_muted_notes(track, measure, string, frets,
                                                              start_beat, duration)}


# =============================================================================
# MARKERS & STRUCTURE
# =============================================================================

@mcp.tool()
def gp_add_marker(measure: int, title: str, color: List[int] = None) -> Dict[str, Any]:
    """Add section marker (e.g., 'Intro', 'Verse', 'Chorus'). Color: [R,G,B]"""
    c = tuple(color) if color else (255, 0, 0)
    return {"success": get_controller().add_marker(measure, title, c)}

@mcp.tool()
def gp_get_markers() -> Dict[str, Any]:
    """Get all markers in the song."""
    return {"markers": get_controller().get_markers()}

@mcp.tool()
def gp_set_repeat_start(measure: int) -> Dict[str, Any]:
    """Mark measure as repeat start."""
    return {"success": get_controller().set_repeat_start(measure)}

@mcp.tool()
def gp_set_repeat_end(measure: int, count: int = 2) -> Dict[str, Any]:
    """Mark measure as repeat end."""
    return {"success": get_controller().set_repeat_end(measure, count)}

@mcp.tool()
def gp_set_alternate_ending(measure: int, endings: List[int]) -> Dict[str, Any]:
    """Set alternate endings (e.g., [1] for 1st, [2] for 2nd)."""
    return {"success": get_controller().set_alternate_ending(measure, endings)}

@mcp.tool()
def gp_set_tempo_change(track: int, measure: int, beat: int, new_tempo: int) -> Dict[str, Any]:
    """Add tempo change at specific position."""
    return {"success": get_controller().set_tempo_change(track, measure, beat, new_tempo)}


# =============================================================================
# COPY/PASTE
# =============================================================================

@mcp.tool()
def gp_copy_measures(track_index: int, start_measure: int, end_measure: int) -> Dict[str, Any]:
    """Copy measures to clipboard."""
    return get_controller().copy_measures(track_index, start_measure, end_measure)

@mcp.tool()
def gp_paste_measures(track_index: int, start_measure: int, repeat: int = 1) -> Dict[str, Any]:
    """Paste clipboard to track."""
    return get_controller().paste_measures(track_index, start_measure, repeat)

@mcp.tool()
def gp_repeat_pattern(track_index: int, source_start: int, source_end: int,
                      dest_start: int, times: int = 1) -> Dict[str, Any]:
    """Copy and paste pattern in one call."""
    return get_controller().repeat_pattern(track_index, source_start, source_end, dest_start, times)

@mcp.tool()
def gp_copy_track_from_file(source_path: str, source_track_index: int,
                            dest_track_name: str = None, start_measure: int = 0,
                            end_measure: int = None) -> Dict[str, Any]:
    """Copy track from another GP file."""
    return get_controller().copy_track_from_file(source_path, source_track_index,
                                                  dest_track_name, start_measure, end_measure)


# =============================================================================
# TRANSPOSE
# =============================================================================

@mcp.tool()
def gp_transpose(track_index: int, semitones: int, start_measure: int = 0,
                 end_measure: int = None) -> Dict[str, Any]:
    """Transpose notes by semitones (positive=up, negative=down)."""
    return get_controller().transpose_track(track_index, semitones, start_measure, end_measure)


# =============================================================================
# READ OPERATIONS
# =============================================================================

@mcp.tool()
def gp_get_tab(track_index: int, start_measure: int = 0, end_measure: int = None) -> Dict[str, Any]:
    """Get ASCII tablature."""
    return {"tab": get_controller().get_tab(track_index, start_measure, end_measure)}

@mcp.tool()
def gp_get_notes(track_index: int) -> Dict[str, Any]:
    """Get all notes from a track."""
    return {"notes": get_controller().get_track_notes(track_index)}

@mcp.tool()
def gp_get_statistics() -> Dict[str, Any]:
    """Get song statistics."""
    return get_controller().get_statistics()


# =============================================================================
# LISTS
# =============================================================================

@mcp.tool()
def gp_list_chords() -> Dict[str, Any]:
    """List all available chord names."""
    return {"chords": get_controller().list_chords()}

@mcp.tool()
def gp_list_templates() -> Dict[str, Any]:
    """List all available riff templates."""
    return {"templates": get_controller().list_riff_templates()}

@mcp.tool()
def gp_list_tunings() -> Dict[str, Any]:
    """List all available tuning presets."""
    from .controller import TUNINGS
    return {"tunings": list(TUNINGS.keys())}
