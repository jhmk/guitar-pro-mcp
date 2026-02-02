"""
Optimized MCP Tools v2.0
- Batch operations for speed
- Reduced tool count (combined functionality)
- Better error handling
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
    # SONG CREATION (FAST!)
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
        Create a complete song in ONE call - fastest way to build songs!
        
        Args:
            title: Song title
            artist: Artist name  
            tempo: BPM
            tracks: List of track configs, e.g.:
                    [{"name": "Lead", "tuning": "drop_d", "instrument": 25},
                     {"name": "Rhythm", "tuning": "drop_d"}]
            measures: Number of measures to create
            notes: List of notes to add (see gp_add_notes for format)
        
        Example - create a song with a power chord riff:
            gp_create_complete(
                title="My Riff",
                tempo=140,
                tracks=[{"name": "Guitar", "tuning": "drop_d"}],
                measures=4,
                notes=[
                    {"measure": 0, "beat": 0, "string": 6, "fret": 0},
                    {"measure": 0, "beat": 1, "string": 6, "fret": 0},
                    {"measure": 0, "beat": 2, "string": 6, "fret": 3},
                    {"measure": 0, "beat": 3, "string": 6, "fret": 5},
                ]
            )
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
        """Get current song info - title, tracks, measures, tempo."""
        try:
            return {"status": "success", "data": ctrl.get_info()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_stats")
    def gp_stats(ctx: Context) -> Dict[str, Any]:
        """Get song statistics - note counts, measures, etc."""
        try:
            return {"status": "success", "data": ctrl.get_statistics()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_set_properties")
    def gp_set_properties(ctx: Context, title: str = None, artist: str = None,
                          album: str = None, tempo: int = None) -> Dict[str, Any]:
        """Update song properties (title, artist, album, tempo)."""
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
            instrument: MIDI instrument number (25=overdriven guitar, 
                        29=distortion guitar, 33=bass)
        """
        try:
            idx = ctrl.add_track(name, tuning, instrument)
            return {"status": "success", "track_index": idx, "data": ctrl.get_tracks()}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_set_tuning")
    def gp_set_tuning(ctx: Context, track_index: int, tuning: str) -> Dict[str, Any]:
        """
        Change track tuning.
        
        Available tunings:
            6-string: standard, drop_d, drop_c, drop_b, drop_a, 
                      d_standard, c_standard, open_d, open_g, dadgad
            7-string: standard_7, drop_a_7
            Bass: bass_standard, bass_drop_d, bass_5_standard
        """
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
        """Add one or more measures. Returns new measure count."""
        try:
            total = ctrl.add_measures(count)
            return {"status": "success", "measure_count": total}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_set_time_signature")
    def gp_set_time_signature(ctx: Context, measure: int, 
                               numerator: int, denominator: int) -> Dict[str, Any]:
        """Set time signature for a measure (e.g., 4/4, 3/4, 6/8)."""
        try:
            ctrl.set_time_signature(measure, numerator, denominator)
            return {"status": "success", "message": f"Set {numerator}/{denominator} at measure {measure}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # NOTE OPERATIONS - BATCH (FAST!)
    # =========================================================================
    
    @mcp.tool("gp_add_notes")
    def gp_add_notes(ctx: Context, notes: List[Dict]) -> Dict[str, Any]:
        """
        Add multiple notes in ONE call - fastest way to add notes!
        
        Each note dict:
            track: int (default 0)
            measure: int (default 0)
            beat: int (default 0)
            string: int (1-6, 1=high E, 6=low E) - REQUIRED
            fret: int (0-24) - REQUIRED
            duration: int (1=whole, 2=half, 4=quarter, 8=eighth, 16=sixteenth)
            palm_mute: bool
            hammer_on: bool
            pull_off: bool
            slide: bool
            bend: bool
            vibrato: bool
            ghost: bool
            dead: bool
        
        Example - add a riff:
            gp_add_notes([
                {"measure": 0, "beat": 0, "string": 6, "fret": 0, "palm_mute": True},
                {"measure": 0, "beat": 1, "string": 6, "fret": 0, "palm_mute": True},
                {"measure": 0, "beat": 2, "string": 6, "fret": 3},
                {"measure": 0, "beat": 3, "string": 6, "fret": 5},
            ])
        """
        try:
            ctrl.add_notes_batch(notes)
            return {"status": "success", "notes_added": len(notes)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_add_note")
    def gp_add_note(ctx: Context, track: int, measure: int, beat: int,
                    string: int, fret: int, duration: int = 4) -> Dict[str, Any]:
        """
        Add a single note (use gp_add_notes for multiple notes - much faster!).
        
        Args:
            track: Track index (0-based)
            measure: Measure index (0-based)
            beat: Beat position within measure (0-based)
            string: String number (1=high E, 6=low E)
            fret: Fret number (0=open)
            duration: Note duration (4=quarter note)
        """
        try:
            ctrl.add_note(track, measure, beat, string, fret, duration)
            return {"status": "success", "message": f"Added fret {fret} on string {string}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # CHORD HELPERS
    # =========================================================================
    
    @mcp.tool("gp_add_power_chord")
    def gp_add_power_chord(ctx: Context, track: int, measure: int, beat: int,
                           root_string: int, root_fret: int,
                           duration: int = 4) -> Dict[str, Any]:
        """
        Add a power chord (root + fifth + octave).
        
        Args:
            root_string: String for root note (typically 5 or 6)
            root_fret: Fret position for root
            
        Example - E5 power chord:
            gp_add_power_chord(track=0, measure=0, beat=0, root_string=6, root_fret=0)
        """
        try:
            ctrl.add_power_chord(track, measure, beat, root_string, root_fret, duration)
            return {"status": "success", "message": f"Added power chord at fret {root_fret}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_add_chord")
    def gp_add_chord(ctx: Context, track: int, measure: int, beat: int,
                     frets: List[int], duration: int = 4) -> Dict[str, Any]:
        """
        Add any chord shape.
        
        Args:
            frets: Fret positions from LOW to HIGH string.
                   Use -1 for muted strings.
                   
        Examples:
            E major:  [0, 2, 2, 1, 0, 0]
            A minor:  [-1, 0, 2, 2, 1, 0]
            G major:  [3, 2, 0, 0, 0, 3]
            F barre:  [1, 3, 3, 2, 1, 1]
        """
        try:
            ctrl.add_chord(track, measure, beat, frets, duration)
            return {"status": "success", "message": "Added chord"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_add_palm_mutes")
    def gp_add_palm_mutes(ctx: Context, track: int, measure: int, string: int,
                          frets: List[int], start_beat: int = 0,
                          duration: int = 8) -> Dict[str, Any]:
        """
        Add a sequence of palm-muted notes (common in metal chugging).
        
        Example - classic 0-0-0-3-0-0-0-5 pattern:
            gp_add_palm_mutes(track=0, measure=0, string=6, 
                              frets=[0, 0, 0, 3, 0, 0, 0, 5])
        """
        try:
            ctrl.add_palm_muted_notes(track, measure, string, frets, start_beat, duration)
            return {"status": "success", "notes_added": len(frets)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # =========================================================================
    # TAB IMPORT/EXPORT
    # =========================================================================
    
    @mcp.tool("gp_import_tab")
    def gp_import_tab(ctx: Context, tab: str, track: int = 0,
                      start_measure: int = 0, duration: int = 8) -> Dict[str, Any]:
        """
        Import ASCII tablature.
        
        Supports two formats:
        
        1. Standard tab:
            e|-----------------|
            B|-----------------|
            G|-----------------|
            D|--0-2-3-2-0------|
            A|-----------------|
            E|--0-0-0-0-0------|
        
        2. Compact format:
            "6:0-0-0-0 4:2-3-2"
            (string:fret-fret-fret)
        """
        try:
            ctrl.import_tab(tab, track, start_measure, duration)
            return {"status": "success", "message": "Tab imported"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_get_tab")
    def gp_get_tab(ctx: Context, track_index: int, start_measure: int = 0,
                   end_measure: int = None) -> Dict[str, Any]:
        """
        Get ASCII tab representation of a track.
        
        Args:
            track_index: Track to display
            start_measure: First measure (default 0)
            end_measure: Last measure (default all)
        """
        try:
            tab = ctrl.get_tab(track_index, start_measure, end_measure)
            return {"status": "success", "tab": tab}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    @mcp.tool("gp_get_notes")
    def gp_get_notes(ctx: Context, track_index: int) -> Dict[str, Any]:
        """Get all notes from a track as a list."""
        try:
            return {"status": "success", "data": ctrl.get_track_notes(track_index)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
