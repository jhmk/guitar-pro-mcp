        "progression" - Add chord progression (track, start_measure, chords=["E","A","B"])
        "palm_mutes" - Add palm-muted sequence (track, measure, string, frets=[0,0,3,5])
        "tab" - Import ASCII tab (tab="e|--0--3--|...", track, start_measure)
        "template" - Add riff template (track, measure, template_name, root_fret, repeat)
    
    Note effects in batch mode:
        palm_mute, hammer_on, pull_off, slide, vibrato, ghost, dead, let_ring,
        staccato, accent, heavy_accent, tap, slap, pop, tied,
        bend ("half"/"full"/"full_half"/"double"), bend_release,
        harmonic ("natural"/"artificial"/"pinch"/"tap"),
        trill (fret), trill_speed (8/16/32),
        tremolo_picking (8/16/32),
        grace_fret, grace_transition ("slide"/"bend"/"hammer")
    """
    ctrl = get_controller()
    
    if mode == "batch":
        return {"success": ctrl.add_notes_batch(notes or [])}
    
    elif mode == "multi_track":
        return ctrl.add_notes_multi_track(notes_by_track or {})
    
    elif mode == "chord":
        if chord_name:
            return {"success": ctrl.add_chord_by_name(track or 0, measure or 0, beat or 0, 
                                                       chord_name, duration or 4)}
        elif frets:
            return {"success": ctrl.add_chord(track or 0, measure or 0, beat or 0, 
                                               frets, duration or 4)}
        return {"error": "Provide chord_name or frets"}
    
    elif mode == "power_chord":
        return {"success": ctrl.add_power_chord(track or 0, measure or 0, beat or 0,
                                                 root_string or 6, root_fret or 0, duration or 4)}
    
    elif mode == "progression":
        return ctrl.add_chord_progression(track or 0, start_measure or 0, chords or [],
                                          beats_per_chord or 4, duration or 4)
    
    elif mode == "palm_mutes":
        return {"success": ctrl.add_palm_muted_notes(track or 0, measure or 0, string or 6,
                                                      frets or [], start_beat or 0, duration or 8)}
    
    elif mode == "tab":
        return ctrl.import_tab_bulk(tab or "", track or 0, start_measure or 0, duration or 8)
    
    elif mode == "template":
        return ctrl.add_riff_template(track or 0, measure or 0, template_name or "chug_basic",
                                      root_fret or 0, repeat or 1)
    
    return {"error": f"Unknown mode: {mode}"}


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
# MARKERS & STRUCTURE
# =============================================================================

@mcp.tool()
def gp_add_marker(measure: int, title: str, color: List[int] = None) -> Dict[str, Any]:
    """Add section marker (e.g., 'Intro', 'Verse', 'Chorus'). Color: [R,G,B]"""
    c = tuple(color) if color else (255, 0, 0)
    return {"success": get_controller().add_marker(measure, title, c)}

@mcp.tool()
def gp_set_repeat(measure: int, repeat_type: str, count: int = 2, 
                  endings: List[int] = None) -> Dict[str, Any]:
    """
    Set repeat structure.
    
    repeat_type:
        "start" - Mark as repeat start
        "end" - Mark as repeat end with count
        "ending" - Set alternate endings (e.g., [1] for 1st, [2] for 2nd)
    """
    ctrl = get_controller()
    
    if repeat_type == "start":
        return {"success": ctrl.set_repeat_start(measure)}
    elif repeat_type == "end":
        return {"success": ctrl.set_repeat_end(measure, count)}
    elif repeat_type == "ending":
        return {"success": ctrl.set_alternate_ending(measure, endings or [1])}
    
    return {"error": f"Unknown repeat_type: {repeat_type}"}

@mcp.tool()
def gp_set_tempo_change(track: int, measure: int, beat: int, new_tempo: int) -> Dict[str, Any]:
    """Add tempo change at specific position."""
    return {"success": get_controller().set_tempo_change(track, measure, beat, new_tempo)}


# =============================================================================
# COPY/PASTE
# =============================================================================

@mcp.tool()
def gp_copy(action: str, track_index: int = None, start_measure: int = None,
            end_measure: int = None, repeat: int = None, dest_start: int = None,
            source_start: int = None, source_end: int = None, times: int = None,
            source_path: str = None, source_track_index: int = None,
            dest_track_name: str = None) -> Dict[str, Any]:
    """
    Copy/paste/repeat operations.
    
    Actions:
        "copy" - Copy measures to clipboard
        "paste" - Paste clipboard (repeat times)
        "repeat" - Copy+paste in one call
        "from_file" - Copy track from another GP file
    """
    ctrl = get_controller()
    
    if action == "copy":
        return ctrl.copy_measures(track_index or 0, start_measure or 0, end_measure or 0)
    elif action == "paste":
        return ctrl.paste_measures(track_index or 0, start_measure or 0, repeat or 1)
    elif action == "repeat":
        return ctrl.repeat_pattern(track_index or 0, source_start or 0, source_end or 0,
                                   dest_start or 0, times or 1)
    elif action == "from_file":
        return ctrl.copy_track_from_file(source_path or "", source_track_index or 0,
                                         dest_track_name, start_measure or 0, end_measure)
    
    return {"error": f"Unknown action: {action}"}


# =============================================================================
# READ OPERATIONS
# =============================================================================

@mcp.tool()
def gp_read(track_index: int, format: str = "tab", start_measure: int = 0,
            end_measure: int = None) -> Dict[str, Any]:
    """
    Read notes from a track.
    
    format: "tab" for ASCII tablature, "notes" for note list
    """
    ctrl = get_controller()
    
    if format == "tab":
        return {"tab": ctrl.get_tab(track_index, start_measure, end_measure)}
    elif format == "notes":
        return {"notes": ctrl.get_track_notes(track_index)}
    
    return {"error": f"Unknown format: {format}"}


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
