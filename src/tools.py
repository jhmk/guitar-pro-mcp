"""
MCP Tools v2.2
- All new features: tab import, pattern repeat, copy from file, chord shortcuts, templates, transpose
"""

from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

from .controller import get_controller


def setup_tools(mcp: FastMCP) -> None:
    """Register all MCP tools."""
    
    ctrl = get_controller()
    
    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================
    
    @mcp.tool("gp_load")
    def gp_load(ctx: Context, file_path: str) -> Dict[str, Any]:
        """
        Load a Guitar Pro file (.gp5, .gp4, .gp3).
        Returns song info including tracks and measures.
        """
        try:
            return {"status": "success", "data": ctrl.load(file_path)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_save")
    def gp_save(ctx: Context, file_path: str) -> Dict[str, Any]:
        """
        Save current song to Guitar Pro 5 format.
        File path should end with .gp5
        """
        try:
            ctrl.save(file_path)
            return {"status": "success", "message": f"Saved: {file_path}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # SONG CREATION
    # =========================================================================
    
    @mcp.tool("gp_create")
    def gp_create(ctx: Context, title: str = "New Song", artist: str = "",
                  tempo: int = 120, tuning: str = "standard") -> Dict[str, Any]:
        """
        Create a new song with one guitar track.
        
        Args:
            title: Song title
            artist: Artist name
            tempo: BPM (default 120)
            tuning: Tuning preset - standard, drop_d, drop_c, drop_b, 
                    d_standard, c_standard, open_d, open_g, dadgad,
                    standard_7, bass_standard, bass_drop_d, etc.
        """
        try:
            return {"status": "success", "data": ctrl.create(title, artist, tempo, tuning)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_create_complete")
    def gp_create_complete(ctx: Context, title: str, artist: str = "",
                           tempo: int = 120, tracks: List[Dict] = None,
                           measures: int = 4, notes: List[Dict] = None) -> Dict[str, Any]:
        """
        Create a complete song in ONE call.
        
        Args:
            title: Song title
            artist: Artist name  
            tempo: BPM
            tracks: List of track configs [{"name": "Lead", "tuning": "drop_d", "instrument": 25}]
            measures: Number of measures to create
            notes: List of notes to add
        """
        try:
            return {"status": "success", "data": ctrl.create_complete(
                title, artist, tempo, tracks, measures, notes
            )}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # SONG INFO
    # =========================================================================
    
    @mcp.tool("gp_info")
    def gp_info(ctx: Context) -> Dict[str, Any]:
        """Get current song info."""
        try:
            return {"status": "success", "data": ctrl.get_info()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_stats")
    def gp_stats(ctx: Context) -> Dict[str, Any]:
        """Get song statistics."""
        try:
            return {"status": "success", "data": ctrl.get_statistics()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_set_properties")
    def gp_set_properties(ctx: Context, title: str = None, artist: str = None,
                          album: str = None, tempo: int = None) -> Dict[str, Any]:
        """Update song properties."""
        try:
            ctrl.set_properties(title, artist, album, tempo)
            return {"status": "success", "data": ctrl.get_info()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # TRACK OPERATIONS
    # =========================================================================
    
    @mcp.tool("gp_add_track")
    def gp_add_track(ctx: Context, name: str, tuning: str = "standard",
                     instrument: int = 25) -> Dict[str, Any]:
        """
        Add a new track.
        
        Args:
            name: Track name
            tuning: Tuning preset (standard, drop_d, drop_c, etc.)
            instrument: MIDI instrument (25=overdriven, 29=distortion, 33=bass)
        """
        try:
            idx = ctrl.add_track(name, tuning, instrument)
            return {"status": "success", "track_index": idx, "data": ctrl.get_tracks()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_set_tuning")
    def gp_set_tuning(ctx: Context, track_index: int, tuning: str) -> Dict[str, Any]:
        """Change track tuning."""
        try:
            ctrl.set_track_tuning(track_index, tuning)
            return {"status": "success", "data": ctrl.get_tracks()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_tracks")
    def gp_tracks(ctx: Context) -> Dict[str, Any]:
        """Get all tracks info."""
        try:
            return {"status": "success", "data": ctrl.get_tracks()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # MEASURE OPERATIONS
    # =========================================================================
    
    @mcp.tool("gp_add_measures")
    def gp_add_measures(ctx: Context, count: int = 1) -> Dict[str, Any]:
        """Add measures. Returns new measure count."""
        try:
            total = ctrl.add_measures(count)
            return {"status": "success", "measure_count": total}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_set_time_signature")
    def gp_set_time_signature(ctx: Context, measure: int, 
                               numerator: int, denominator: int) -> Dict[str, Any]:
        """Set time signature for a measure."""
        try:
            ctrl.set_time_signature(measure, numerator, denominator)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # NOTE OPERATIONS
    # =========================================================================
    
    @mcp.tool("gp_add_notes")
    def gp_add_notes(ctx: Context, notes: List[Dict]) -> Dict[str, Any]:
        """
        Add multiple notes in ONE call - fastest way!
        
        Each note: {track, measure, beat (INTEGER!), string (1-6), fret (0-24), 
                    duration, palm_mute, hammer_on, slide, vibrato, ghost, dead}
        """
        try:
            ctrl.add_notes_batch(notes)
            return {"status": "success", "notes_added": len(notes)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_add_note")
    def gp_add_note(ctx: Context, track: int, measure: int, beat: int,
                    string: int, fret: int, duration: int = 4) -> Dict[str, Any]:
        """Add a single note."""
        try:
            ctrl.add_note(track, measure, beat, string, fret, duration)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # TAB BULK IMPORT (NEW!)
    # =========================================================================
    
    @mcp.tool("gp_import_tab")
    def gp_import_tab(ctx: Context, tab: str, track: int = 0,
                      start_measure: int = 0, duration: int = 8) -> Dict[str, Any]:
        """
        Import complete ASCII tablature - THE FASTEST WAY TO ADD MUSIC!
        
        Supports standard format:
            e|--0--3--5--|
            B|-----------|
            G|-----------|
            D|-----------|
            A|-----------|
            E|--0--0--0--|
        
        Or compact format:
            "6:0-0-0-0 5:2-3-5 4:2-4-5"
            (string:fret-fret-fret)
        """
        try:
            result = ctrl.import_tab_bulk(tab, track, start_measure, duration)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # PATTERN COPY/REPEAT (NEW!)
    # =========================================================================
    
    @mcp.tool("gp_copy_measures")
    def gp_copy_measures(ctx: Context, track_index: int, 
                         start_measure: int, end_measure: int) -> Dict[str, Any]:
        """Copy measures to clipboard for later pasting."""
        try:
            result = ctrl.copy_measures(track_index, start_measure, end_measure)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_paste_measures")
    def gp_paste_measures(ctx: Context, track_index: int, start_measure: int,
                          repeat: int = 1) -> Dict[str, Any]:
        """Paste clipboard content, optionally repeating."""
        try:
            result = ctrl.paste_measures(track_index, start_measure, repeat)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_repeat_pattern")
    def gp_repeat_pattern(ctx: Context, track_index: int, source_start: int,
                          source_end: int, dest_start: int, 
                          times: int = 1) -> Dict[str, Any]:
        """
        Copy a pattern and repeat it - great for riffs!
        
        Example: Copy measures 0-1 and repeat 4 times starting at measure 2:
            gp_repeat_pattern(0, 0, 1, 2, 4)
        """
        try:
            result = ctrl.repeat_pattern(track_index, source_start, source_end, 
                                        dest_start, times)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # COPY FROM EXISTING FILE (NEW!)
    # =========================================================================
    
    @mcp.tool("gp_copy_track_from_file")
    def gp_copy_track_from_file(ctx: Context, source_path: str, 
                                 source_track_index: int,
                                 dest_track_name: str = None,
                                 start_measure: int = 0,
                                 end_measure: int = None) -> Dict[str, Any]:
        """
        Copy a track from another Guitar Pro file.
        
        Example: Copy track 0 (Guitar 1) from original file:
            gp_copy_track_from_file("/path/to/original.gp5", 0, "Guitar 1 Copy")
        """
        try:
            result = ctrl.copy_track_from_file(source_path, source_track_index,
                                               dest_track_name, start_measure,
                                               end_measure)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # CHORD SHORTCUTS (NEW!)
    # =========================================================================
    
    @mcp.tool("gp_add_chord")
    def gp_add_chord(ctx: Context, track: int, measure: int, beat: int,
                     chord_name: str = None, frets: List[int] = None,
                     duration: int = 4) -> Dict[str, Any]:
        """
        Add a chord by name OR fret positions.
        
        By name: gp_add_chord(0, 0, 0, chord_name="E")
        By frets: gp_add_chord(0, 0, 0, frets=[0, 2, 2, 1, 0, 0])
        
        Available chords: E, Em, A, Am, D, Dm, G, C, F, B, Bm,
                          E5, A5, D5, G5, C5, F5, B5 (power chords),
                          E7, A7, D7, G7, Em7, Am7, Dm7,
                          Asus2, Asus4, Dsus2, Dsus4
        """
        try:
            if chord_name:
                ctrl.add_chord_by_name(track, measure, beat, chord_name, duration)
            elif frets:
                ctrl.add_chord(track, measure, beat, frets, duration)
            else:
                return {"status": "error", "message": "Provide chord_name or frets"}
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_add_power_chord")
    def gp_add_power_chord(ctx: Context, track: int, measure: int, beat: int,
                           root_string: int, root_fret: int,
                           duration: int = 4) -> Dict[str, Any]:
        """Add a power chord (root + fifth + octave)."""
        try:
            ctrl.add_power_chord(track, measure, beat, root_string, root_fret, duration)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_add_chord_progression")
    def gp_add_chord_progression(ctx: Context, track: int, start_measure: int,
                                  chords: List[str], beats_per_chord: int = 4,
                                  duration: int = 4) -> Dict[str, Any]:
        """
        Add a chord progression.
        
        Example: gp_add_chord_progression(0, 0, ["E", "A", "B", "E"])
        """
        try:
            result = ctrl.add_chord_progression(track, start_measure, chords,
                                               beats_per_chord, duration)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_list_chords")
    def gp_list_chords(ctx: Context) -> Dict[str, Any]:
        """List available chord names."""
        try:
            return {"status": "success", "chords": ctrl.list_chords()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # RIFF TEMPLATES (NEW!)
    # =========================================================================
    
    @mcp.tool("gp_list_riff_templates")
    def gp_list_riff_templates(ctx: Context) -> Dict[str, Any]:
        """List available riff templates."""
        try:
            return {"status": "success", "templates": ctrl.list_riff_templates()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_add_riff_template")
    def gp_add_riff_template(ctx: Context, track: int, measure: int,
                              template_name: str, root_fret: int = 0,
                              repeat: int = 1) -> Dict[str, Any]:
        """
        Add a riff template.
        
        Templates: chug_basic, chug_gallop, chug_breakdown, 
                   power_quarters, djent_basic, thrash_pick
        
        Example: gp_add_riff_template(0, 0, "chug_basic", root_fret=3, repeat=4)
        """
        try:
            result = ctrl.add_riff_template(track, measure, template_name, 
                                           root_fret, repeat)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # MULTI-TRACK BATCH (NEW!)
    # =========================================================================
    
    @mcp.tool("gp_add_notes_multi_track")
    def gp_add_notes_multi_track(ctx: Context, 
                                  notes_by_track: Dict[int, List[Dict]]) -> Dict[str, Any]:
        """
        Add notes to multiple tracks at once.
        
        Example: {0: [guitar notes...], 1: [bass notes...]}
        """
        try:
            result = ctrl.add_notes_multi_track(notes_by_track)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # TRANSPOSE (NEW!)
    # =========================================================================
    
    @mcp.tool("gp_transpose")
    def gp_transpose(ctx: Context, track_index: int, semitones: int,
                     start_measure: int = 0, end_measure: int = None) -> Dict[str, Any]:
        """
        Transpose notes in a track.
        
        Args:
            semitones: Positive = up, negative = down
            start_measure: First measure (default: 0)
            end_measure: Last measure (default: all)
        
        Example: Transpose track 0 down 2 semitones:
            gp_transpose(0, -2)
        """
        try:
            result = ctrl.transpose_track(track_index, semitones, 
                                         start_measure, end_measure)
            return {"status": "success", **result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # PALM MUTES
    # =========================================================================
    
    @mcp.tool("gp_add_palm_mutes")
    def gp_add_palm_mutes(ctx: Context, track: int, measure: int, string: int,
                          frets: List[int], start_beat: int = 0,
                          duration: int = 8) -> Dict[str, Any]:
        """
        Add palm-muted notes.
        
        Example: gp_add_palm_mutes(0, 0, 6, [0, 0, 0, 3, 0, 0, 0, 5])
        """
        try:
            ctrl.add_palm_muted_notes(track, measure, string, frets, start_beat, duration)
            return {"status": "success", "notes_added": len(frets)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # TAB EXPORT
    # =========================================================================
    
    @mcp.tool("gp_get_tab")
    def gp_get_tab(ctx: Context, track_index: int, start_measure: int = 0,
                   end_measure: int = None) -> Dict[str, Any]:
        """Get ASCII tab representation."""
        try:
            tab = ctrl.get_tab(track_index, start_measure, end_measure)
            return {"status": "success", "tab": tab}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_get_notes")
    def gp_get_notes(ctx: Context, track_index: int) -> Dict[str, Any]:
        """Get all notes from a track as list."""
        try:
            return {"status": "success", "data": ctrl.get_track_notes(track_index)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
