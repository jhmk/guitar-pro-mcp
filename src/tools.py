"""
MCP Tools v3.0
- Consolidated from 30 tools down to 8 for faster LLM dispatch
- All controller logic unchanged; routing happens here via action/mode/format params
"""

from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP, Context

from .controller import get_controller


def setup_tools(mcp: FastMCP) -> None:
    """Register all MCP tools (8 consolidated tools)."""

    ctrl = get_controller()

    # =========================================================================
    # 1. gp_create — simple or complete song creation
    # =========================================================================

    @mcp.tool("gp_create")
    def gp_create(ctx: Context, title: str = "New Song", artist: str = "",
                  tempo: int = 120, tuning: str = "standard",
                  tracks: Optional[List[Dict]] = None, measures: int = 4,
                  notes: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Create a new Guitar Pro song.

        Simple: gp_create("My Song")
        Full:   gp_create("My Song", tracks=[{"name":"Lead","tuning":"drop_d"}], notes=[...])

        Args:
            title: Song title
            artist: Artist name
            tempo: BPM (default 120)
            tuning: Tuning preset (standard, drop_d, drop_c, drop_b, d_standard,
                    c_standard, open_d, open_g, dadgad, standard_7, bass_standard, etc.)
            tracks: Optional list of track configs [{"name":"Lead", "tuning":"drop_d", "instrument":25}]
            measures: Number of measures (default 4, used with tracks/notes)
            notes: Optional list of notes to add immediately
        """
        try:
            if tracks is not None or notes is not None:
                return {"status": "success", "data": ctrl.create_complete(
                    title, artist, tempo, tracks, measures, notes
                )}
            else:
                return {"status": "success", "data": ctrl.create(title, artist, tempo, tuning)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # 2. gp_load — load a file
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

    # =========================================================================
    # 3. gp_save — save to file
    # =========================================================================

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
    # 4. gp_info — song info with optional extras
    # =========================================================================

    @mcp.tool("gp_info")
    def gp_info(ctx: Context, include: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get song info. Always returns basic info + track list.

        Optional include list for extras:
            "stats"     — song statistics (note counts, etc.)
            "chords"    — available chord names
            "templates" — available riff template names

        Examples:
            gp_info()                        — basic info only
            gp_info(include=["stats"])       — info + statistics
            gp_info(include=["chords","templates"]) — info + chords + templates
        """
        try:
            result = {"status": "success", "data": ctrl.get_info()}
            if include:
                if "stats" in include:
                    result["stats"] = ctrl.get_statistics()
                if "chords" in include:
                    result["chords"] = ctrl.list_chords()
                if "templates" in include:
                    result["templates"] = ctrl.list_riff_templates()
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # 5. gp_edit — structural edits dispatched by action
    # =========================================================================

    @mcp.tool("gp_edit")
    def gp_edit(ctx: Context, action: str,
                # set_properties
                title: Optional[str] = None, artist: Optional[str] = None,
                album: Optional[str] = None, tempo: Optional[int] = None,
                # add_track
                name: Optional[str] = None, tuning: Optional[str] = None,
                instrument: Optional[int] = None,
                # set_tuning / transpose
                track_index: Optional[int] = None,
                # add_measures
                count: Optional[int] = None,
                # set_time_signature
                measure: Optional[int] = None,
                numerator: Optional[int] = None, denominator: Optional[int] = None,
                # transpose
                semitones: Optional[int] = None,
                start_measure: Optional[int] = None,
                end_measure: Optional[int] = None) -> Dict[str, Any]:
        """
        Edit song structure. Dispatches by action parameter.

        Actions:
            "set_properties" — Update title, artist, album, tempo
            "add_track"      — Add track (name, tuning="standard", instrument=25)
            "set_tuning"     — Change track tuning (track_index, tuning)
            "add_measures"   — Add measures (count=1)
            "set_time_signature" — Set time sig (measure, numerator, denominator)
            "transpose"      — Transpose notes (track_index, semitones, start_measure, end_measure)

        Examples:
            gp_edit(action="set_properties", title="New Title", tempo=140)
            gp_edit(action="add_track", name="Bass", tuning="bass_standard", instrument=33)
            gp_edit(action="set_tuning", track_index=0, tuning="drop_d")
            gp_edit(action="add_measures", count=8)
            gp_edit(action="set_time_signature", measure=0, numerator=3, denominator=4)
            gp_edit(action="transpose", track_index=0, semitones=-2)
        """
        try:
            if action == "set_properties":
                ctrl.set_properties(title, artist, album, tempo)
                return {"status": "success", "data": ctrl.get_info()}

            elif action == "add_track":
                idx = ctrl.add_track(
                    name or "New Track",
                    tuning or "standard",
                    instrument if instrument is not None else 25
                )
                return {"status": "success", "track_index": idx, "data": ctrl.get_tracks()}

            elif action == "set_tuning":
                if track_index is None or tuning is None:
                    return {"status": "error", "message": "set_tuning requires track_index and tuning"}
                ctrl.set_track_tuning(track_index, tuning)
                return {"status": "success", "data": ctrl.get_tracks()}

            elif action == "add_measures":
                total = ctrl.add_measures(count if count is not None else 1)
                return {"status": "success", "measure_count": total}

            elif action == "set_time_signature":
                if measure is None or numerator is None or denominator is None:
                    return {"status": "error", "message": "set_time_signature requires measure, numerator, denominator"}
                ctrl.set_time_signature(measure, numerator, denominator)
                return {"status": "success"}

            elif action == "transpose":
                if track_index is None or semitones is None:
                    return {"status": "error", "message": "transpose requires track_index and semitones"}
                result = ctrl.transpose_track(
                    track_index, semitones,
                    start_measure if start_measure is not None else 0,
                    end_measure
                )
                return {"status": "success", **result}

            else:
                return {"status": "error", "message": f"Unknown action: {action}. Use: set_properties, add_track, set_tuning, add_measures, set_time_signature, transpose"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # 6. gp_add_notes — all note-adding operations dispatched by mode
    # =========================================================================

    @mcp.tool("gp_add_notes")
    def gp_add_notes(ctx: Context, mode: str = "batch",
                     # batch / multi_track
                     notes: Optional[List[Dict]] = None,
                     notes_by_track: Optional[Dict[int, List[Dict]]] = None,
                     # common positional
                     track: Optional[int] = None,
                     measure: Optional[int] = None,
                     beat: Optional[int] = None,
                     # chord
                     chord_name: Optional[str] = None,
                     frets: Optional[List[int]] = None,
                     duration: Optional[int] = None,
                     # power_chord
                     root_string: Optional[int] = None,
                     root_fret: Optional[int] = None,
                     # progression
                     start_measure: Optional[int] = None,
                     chords: Optional[List[str]] = None,
                     beats_per_chord: Optional[int] = None,
                     # palm_mutes
                     string: Optional[int] = None,
                     start_beat: Optional[int] = None,
                     # tab
                     tab: Optional[str] = None,
                     # template
                     template_name: Optional[str] = None,
                     repeat: Optional[int] = None) -> Dict[str, Any]:
        """
        Add notes/chords/tabs to the song. Dispatches by mode parameter.

        Modes:
            "batch" (default) — Add notes list [{track, measure, beat, string, fret, duration, palm_mute, hammer_on, slide, vibrato, ghost, dead}]
            "multi_track"     — Add to multiple tracks: notes_by_track={0:[...], 1:[...]}
            "chord"           — Add chord by name or frets (track, measure, beat, chord_name OR frets, duration=4)
            "power_chord"     — Add power chord (track, measure, beat, root_string, root_fret, duration=4)
            "progression"     — Add chord progression (track, start_measure, chords=["E","A","B"], beats_per_chord=4, duration=4)
            "palm_mutes"      — Add palm-muted sequence (track, measure, string, frets=[0,0,3,5], start_beat=0, duration=8)
            "tab"             — Import ASCII tab (tab="e|--0--3--|...", track=0, start_measure=0, duration=8)
            "template"        — Add riff template (track, measure, template_name, root_fret=0, repeat=1)

        Available chords: E, Em, A, Am, D, Dm, G, C, F, B, Bm, E5, A5, D5, G5, C5, F5, B5,
                          E7, A7, D7, G7, Em7, Am7, Dm7, Asus2, Asus4, Dsus2, Dsus4

        Templates: chug_basic, chug_gallop, chug_breakdown, power_quarters, djent_basic, thrash_pick
        """
        try:
            if mode == "batch":
                if not notes:
                    return {"status": "error", "message": "batch mode requires notes list"}
                ctrl.add_notes_batch(notes)
                return {"status": "success", "notes_added": len(notes)}

            elif mode == "multi_track":
                if not notes_by_track:
                    return {"status": "error", "message": "multi_track mode requires notes_by_track"}
                result = ctrl.add_notes_multi_track(notes_by_track)
                return {"status": "success", **result}

            elif mode == "chord":
                t = track if track is not None else 0
                m = measure if measure is not None else 0
                b = beat if beat is not None else 0
                d = duration if duration is not None else 4
                if chord_name:
                    ctrl.add_chord_by_name(t, m, b, chord_name, d)
                elif frets:
                    ctrl.add_chord(t, m, b, frets, d)
                else:
                    return {"status": "error", "message": "chord mode requires chord_name or frets"}
                return {"status": "success"}

            elif mode == "power_chord":
                if root_string is None or root_fret is None:
                    return {"status": "error", "message": "power_chord mode requires root_string and root_fret"}
                t = track if track is not None else 0
                m = measure if measure is not None else 0
                b = beat if beat is not None else 0
                d = duration if duration is not None else 4
                ctrl.add_power_chord(t, m, b, root_string, root_fret, d)
                return {"status": "success"}

            elif mode == "progression":
                if not chords:
                    return {"status": "error", "message": "progression mode requires chords list"}
                t = track if track is not None else 0
                sm = start_measure if start_measure is not None else 0
                bpc = beats_per_chord if beats_per_chord is not None else 4
                d = duration if duration is not None else 4
                result = ctrl.add_chord_progression(t, sm, chords, bpc, d)
                return {"status": "success", **result}

            elif mode == "palm_mutes":
                if not frets:
                    return {"status": "error", "message": "palm_mutes mode requires frets list"}
                t = track if track is not None else 0
                m = measure if measure is not None else 0
                s = string if string is not None else 6
                sb = start_beat if start_beat is not None else 0
                d = duration if duration is not None else 8
                ctrl.add_palm_muted_notes(t, m, s, frets, sb, d)
                return {"status": "success", "notes_added": len(frets)}

            elif mode == "tab":
                if not tab:
                    return {"status": "error", "message": "tab mode requires tab string"}
                t = track if track is not None else 0
                sm = start_measure if start_measure is not None else 0
                d = duration if duration is not None else 8
                result = ctrl.import_tab_bulk(tab, t, sm, d)
                return {"status": "success", **result}

            elif mode == "template":
                if not template_name:
                    return {"status": "error", "message": "template mode requires template_name"}
                t = track if track is not None else 0
                m = measure if measure is not None else 0
                rf = root_fret if root_fret is not None else 0
                r = repeat if repeat is not None else 1
                result = ctrl.add_riff_template(t, m, template_name, rf, r)
                return {"status": "success", **result}

            else:
                return {"status": "error", "message": f"Unknown mode: {mode}. Use: batch, multi_track, chord, power_chord, progression, palm_mutes, tab, template"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # 7. gp_read — read notes as tab or note list
    # =========================================================================

    @mcp.tool("gp_read")
    def gp_read(ctx: Context, track_index: int, format: str = "tab",
                start_measure: int = 0,
                end_measure: Optional[int] = None) -> Dict[str, Any]:
        """
        Read notes from a track.

        Args:
            track_index: Track number (0-based)
            format: "tab" for ASCII tablature, "notes" for note list
            start_measure: First measure to read (default 0)
            end_measure: Last measure (default: all)

        Examples:
            gp_read(track_index=0)                    — full tab
            gp_read(track_index=0, format="notes")    — note list
            gp_read(track_index=0, start_measure=4, end_measure=8) — partial tab
        """
        try:
            if format == "tab":
                tab = ctrl.get_tab(track_index, start_measure, end_measure)
                return {"status": "success", "tab": tab}
            elif format == "notes":
                return {"status": "success", "data": ctrl.get_track_notes(track_index)}
            else:
                return {"status": "error", "message": f"Unknown format: {format}. Use: tab, notes"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # 8. gp_copy — copy/paste/repeat operations
    # =========================================================================

    @mcp.tool("gp_copy")
    def gp_copy(ctx: Context, action: str,
                # common
                track_index: Optional[int] = None,
                start_measure: Optional[int] = None,
                end_measure: Optional[int] = None,
                # paste / repeat
                repeat: Optional[int] = None,
                # repeat
                source_start: Optional[int] = None,
                source_end: Optional[int] = None,
                dest_start: Optional[int] = None,
                times: Optional[int] = None,
                # from_file
                source_path: Optional[str] = None,
                source_track_index: Optional[int] = None,
                dest_track_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Copy/paste/repeat operations. Dispatches by action parameter.

        Actions:
            "copy"      — Copy measures to clipboard (track_index, start_measure, end_measure)
            "paste"     — Paste clipboard (track_index, start_measure, repeat=1)
            "repeat"    — Copy+paste in one call (track_index, source_start, source_end, dest_start, times=1)
            "from_file" — Copy track from another .gp5 file (source_path, source_track_index, dest_track_name, start_measure, end_measure)

        Examples:
            gp_copy(action="copy", track_index=0, start_measure=0, end_measure=1)
            gp_copy(action="paste", track_index=0, start_measure=4, repeat=2)
            gp_copy(action="repeat", track_index=0, source_start=0, source_end=1, dest_start=2, times=4)
            gp_copy(action="from_file", source_path="/path/to/file.gp5", source_track_index=0)
        """
        try:
            if action == "copy":
                if track_index is None or start_measure is None or end_measure is None:
                    return {"status": "error", "message": "copy requires track_index, start_measure, end_measure"}
                result = ctrl.copy_measures(track_index, start_measure, end_measure)
                return {"status": "success", **result}

            elif action == "paste":
                if track_index is None or start_measure is None:
                    return {"status": "error", "message": "paste requires track_index, start_measure"}
                r = repeat if repeat is not None else 1
                result = ctrl.paste_measures(track_index, start_measure, r)
                return {"status": "success", **result}

            elif action == "repeat":
                if track_index is None or source_start is None or source_end is None or dest_start is None:
                    return {"status": "error", "message": "repeat requires track_index, source_start, source_end, dest_start"}
                t = times if times is not None else 1
                result = ctrl.repeat_pattern(track_index, source_start, source_end, dest_start, t)
                return {"status": "success", **result}

            elif action == "from_file":
                if source_path is None or source_track_index is None:
                    return {"status": "error", "message": "from_file requires source_path, source_track_index"}
                result = ctrl.copy_track_from_file(
                    source_path, source_track_index,
                    dest_track_name,
                    start_measure if start_measure is not None else 0,
                    end_measure
                )
                return {"status": "success", **result}

            else:
                return {"status": "error", "message": f"Unknown action: {action}. Use: copy, paste, repeat, from_file"}

        except Exception as e:
            return {"status": "error", "message": str(e)}
