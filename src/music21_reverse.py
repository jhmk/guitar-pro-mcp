"""
music21-to-Guitar-Pro conversion helpers.

This module keeps the reverse conversion path separate from the forward
music21 adapter so the controller can delegate track rebuilding without
embedding conversion policy in its own methods.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import guitarpro as gp
from music21 import stream, tempo

from .fingering import (
    FingeringState,
    StringFretPosition,
    choose_position,
    choose_positions,
    optimize_phrase,
)


def part_to_gp_track_data(
    part: stream.Part,
    tuning_midi: Optional[List[int]] = None,
    strategy: str = "lowest_fret",
    max_fret: int = 24,
) -> Dict[str, object]:
    """
    Convert a music21 part into structured Guitar Pro track data.

    The output is controller-friendly and can be applied directly to a GP track.
    """
    if tuning_midi is None:
        tuning_midi = [64, 59, 55, 50, 45, 40]

    measures_data: List[Dict[str, object]] = []
    note_events: List[Dict[str, int | bool]] = []
    fingering_state = FingeringState()

    measures = list(part.getElementsByClass(stream.Measure))
    for measure_index, measure in enumerate(measures):
        measure_data = {"voices": [], "tempo_changes": []}
        voices = list(measure.getElementsByClass(stream.Voice))
        if not voices:
            synthetic_voice = stream.Voice(id=f"synthetic-{measure_index}")
            for element in measure.notesAndRests:
                synthetic_voice.insert(float(element.offset), element)
            voices = [synthetic_voice]

        for tempo_mark in measure.getElementsByClass(tempo.MetronomeMark):
            if tempo_mark.number is None:
                continue
            measure_data["tempo_changes"].append(
                {
                    "start_ticks": int(round(float(tempo_mark.offset) * gp.models.Duration.quarterTime)),
                    "tempo": int(tempo_mark.number),
                }
            )

        for voice_index, voice in enumerate(voices):
            beats = _voice_to_gp_beats(
                voice,
                tuning_midi=tuning_midi,
                strategy=strategy,
                max_fret=max_fret,
                state=fingering_state,
            )
            for beat_data in beats:
                note_events.extend(
                    _beat_data_to_note_events(
                        beat_data,
                        track_index=0,
                        measure_index=measure_index,
                        voice_index=voice_index,
                    )
                )

            measure_data["voices"].append({"beats": sorted(beats, key=lambda beat: beat["start_ticks"])})

        measures_data.append(measure_data)

    return {"measure_count": len(measures_data), "measures": measures_data, "note_events": note_events}


def write_gp_track_data_to_track(track, track_data: Dict[str, object]) -> int:
    """Apply converted track data to an existing PyGuitarPro track."""
    measures_data = track_data.get("measures", [])
    notes_written = 0

    for measure_index, measure in enumerate(track.measures):
        measure.voices = []
        source_measure = measures_data[measure_index] if measure_index < len(measures_data) else {"voices": []}
        for voice_data in source_measure.get("voices", []):
            voice = gp.models.Voice(measure)
            measure.voices.append(voice)
            for beat_data in voice_data.get("beats", []):
                beat = gp.models.Beat(voice)
                beat.start = int(beat_data.get("start_ticks", len(voice.beats) * gp.models.Duration.quarterTime))
                beat.duration = _build_gp_duration(beat_data)
                for note_data in beat_data.get("notes", []):
                    note = gp.models.Note(beat)
                    note.string = int(note_data["string"])
                    note.value = int(note_data["fret"])
                    if note_data.get("tied"):
                        note.type = gp.NoteType.tie
                    _apply_note_effects(note, note_data)
                    beat.notes.append(note)
                    notes_written += 1
                _apply_beat_effects(beat, beat_data.get("beat_effect", {}))
                voice.beats.append(beat)

        _apply_tempo_changes(measure, source_measure.get("tempo_changes", []))

        if not measure.voices:
            measure.voices.append(gp.models.Voice(measure))

    return notes_written


def part_to_note_events(
    part: stream.Part,
    track_index: int = 0,
    tuning_midi: Optional[List[int]] = None,
    strategy: str = "lowest_fret",
    max_fret: int = 24,
) -> List[Dict[str, int | bool]]:
    """Compatibility wrapper returning flat note events for a part."""
    track_data = part_to_gp_track_data(
        part,
        tuning_midi=tuning_midi,
        strategy=strategy,
        max_fret=max_fret,
    )
    events = list(track_data["note_events"])
    for event in events:
        event["track"] = track_index
    return events


def pitch_to_string_fret(
    midi_pitch: int,
    tuning_midi: List[int],
    strategy: str = "lowest_fret",
    max_fret: int = 24,
) -> Optional[StringFretPosition]:
    """Map a MIDI pitch to a guitar position using the fingering policy layer."""
    return choose_position(
        midi_pitch,
        tuning_midi=tuning_midi,
        strategy=strategy,
        max_fret=max_fret,
    )


def quarter_length_to_gp_duration(quarter_length: float) -> int:
    """Convert a quarter length into the closest supported GP duration."""
    supported = [1, 2, 4, 8, 16, 32, 64]
    return min(supported, key=lambda value: abs((4.0 / float(value)) - quarter_length))


def _element_to_gp_beat_data(
    element,
    tuning_midi,
    strategy: str,
    max_fret: int,
    state: Optional[FingeringState] = None,
) -> Optional[Dict[str, object]]:
    ordered_pitches = _ordered_element_pitches(element)
    positions = choose_positions(
        [pitch_value.midi for pitch_value in ordered_pitches],
        tuning_midi=tuning_midi,
        strategy=strategy,
        max_fret=max_fret,
        state=state,
    )
    if positions is None:
        return None

    matched_metadata = _match_note_metadata_list(element, positions, tuning_midi)
    mapped_notes = [
        _build_note_data(
            element,
            position,
            tuning_midi=tuning_midi,
            note_metadata=note_metadata,
        )
        for position, note_metadata in zip(positions, matched_metadata)
    ]

    duration_obj = getattr(element, "duration", None)
    quarter_length = float(duration_obj.quarterLength) if duration_obj is not None else 1.0
    tuplet = None
    tuplets = list(getattr(duration_obj, "tuplets", [])) if duration_obj is not None else []
    if tuplets:
        tuplet = {
            "enters": int(tuplets[0].numberNotesActual),
            "times": int(tuplets[0].numberNotesNormal),
        }

    return {
        "duration": quarter_length_to_gp_duration(quarter_length),
        "is_dotted": bool(getattr(duration_obj, "dots", 0)),
        "tuplet": tuplet,
        "notes": mapped_notes,
        "beat_effect": _extract_beat_effect_metadata(element),
    }


def _voice_to_gp_beats(
    voice,
    tuning_midi,
    strategy: str,
    max_fret: int,
    state: Optional[FingeringState] = None,
) -> List[Dict[str, object]]:
    elements = list(voice.notesAndRests)
    if strategy != "phrase_aware":
        beats = []
        for element in elements:
            if getattr(element, "isRest", False):
                continue
            beat_data = _element_to_gp_beat_data(
                element,
                tuning_midi=tuning_midi,
                strategy=strategy,
                max_fret=max_fret,
                state=state,
            )
            if beat_data is None:
                continue
            beat_data["start_ticks"] = int(round(float(element.offset) * gp.models.Duration.quarterTime))
            beats.append(beat_data)
        return beats

    beats = []
    for segment in _segment_phrase_elements(elements):
        chosen_positions = optimize_phrase(
            [[pitch_value.midi for pitch_value in _ordered_element_pitches(element)] for element in segment],
            tuning_midi=tuning_midi,
            max_fret=max_fret,
        )
        for element, positions in zip(segment, chosen_positions):
            if positions is None:
                continue
            beats.append(_positions_to_beat_data(element, positions, tuning_midi))
    return beats


def _ordered_element_pitches(element) -> List[object]:
    pitches = element.pitches if hasattr(element, "pitches") else [element.pitch]
    return sorted(pitches, key=lambda pitch_value: pitch_value.midi)


def _positions_to_beat_data(
    element,
    positions: List[StringFretPosition],
    tuning_midi: List[int],
) -> Dict[str, object]:
    duration_obj = getattr(element, "duration", None)
    quarter_length = float(duration_obj.quarterLength) if duration_obj is not None else 1.0
    tuplet = None
    tuplets = list(getattr(duration_obj, "tuplets", [])) if duration_obj is not None else []
    if tuplets:
        tuplet = {
            "enters": int(tuplets[0].numberNotesActual),
            "times": int(tuplets[0].numberNotesNormal),
        }

    return {
        "duration": quarter_length_to_gp_duration(quarter_length),
        "is_dotted": bool(getattr(duration_obj, "dots", 0)),
        "tuplet": tuplet,
        "notes": [
            _build_note_data(
                element,
                position,
                tuning_midi=tuning_midi,
                note_metadata=note_metadata,
            )
            for position, note_metadata in zip(
                positions,
                _match_note_metadata_list(element, positions, tuning_midi),
            )
        ],
        "start_ticks": int(round(float(element.offset) * gp.models.Duration.quarterTime)),
        "beat_effect": _extract_beat_effect_metadata(element),
    }


def _segment_phrase_elements(elements, large_jump_threshold: int = 9) -> List[List[object]]:
    segments: List[List[object]] = []
    current_segment: List[object] = []
    previous_pitches: Optional[List[int]] = None

    for element in elements:
        if getattr(element, "isRest", False):
            if current_segment:
                segments.append(current_segment)
                current_segment = []
            previous_pitches = None
            continue

        current_pitches = [pitch_value.midi for pitch_value in _ordered_element_pitches(element)]
        if current_segment and _should_break_phrase(previous_pitches, current_pitches, large_jump_threshold):
            segments.append(current_segment)
            current_segment = []

        current_segment.append(element)
        previous_pitches = current_pitches

    if current_segment:
        segments.append(current_segment)
    return segments


def _should_break_phrase(
    previous_pitches: Optional[List[int]],
    current_pitches: List[int],
    large_jump_threshold: int,
) -> bool:
    if not previous_pitches:
        return False
    smallest_jump = min(abs(current - previous) for current in current_pitches for previous in previous_pitches)
    return smallest_jump >= large_jump_threshold


def _build_gp_duration(beat_data: Dict[str, object]):
    result = gp.models.Duration()
    result.value = int(beat_data.get("duration", 4))
    result.isDotted = bool(beat_data.get("is_dotted", False))

    tuplet = beat_data.get("tuplet")
    if tuplet:
        result.tuplet.enters = int(tuplet["enters"])
        result.tuplet.times = int(tuplet["times"])
    return result


def _build_note_data(
    element,
    position: StringFretPosition,
    tuning_midi: List[int],
    note_metadata: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    note_data = {
        "string": position.string,
        "fret": position.fret,
        "tied": getattr(getattr(element, "tie", None), "type", None) is not None,
    }
    if note_metadata:
        for key, value in note_metadata.items():
            if key != "midi":
                note_data[key] = value
    return note_data


def _extract_element_gp_metadata(element) -> Dict[str, object]:
    metadata = getattr(element, "_gp_metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _extract_beat_effect_metadata(element) -> Dict[str, object]:
    return dict(_extract_element_gp_metadata(element).get("beat_effect", {}))


def _match_note_metadata_list(
    element,
    positions: List[StringFretPosition],
    tuning_midi: List[int],
) -> List[Dict[str, object]]:
    remaining_effects = list(_extract_element_gp_metadata(element).get("note_effects", []))
    matched: List[Dict[str, object]] = []

    for position in positions:
        string_index = position.string - 1
        midi_pitch = None
        if 0 <= string_index < len(tuning_midi):
            midi_pitch = tuning_midi[string_index] + position.fret

        selected_index = 0
        if midi_pitch is not None:
            for metadata_index, metadata in enumerate(remaining_effects):
                if int(metadata.get("midi", -1)) == midi_pitch:
                    selected_index = metadata_index
                    break

        selected_metadata = dict(remaining_effects.pop(selected_index)) if remaining_effects else {}
        matched.append(selected_metadata)

    return matched


def _beat_data_to_note_events(
    beat_data: Dict[str, object],
    track_index: int,
    measure_index: int,
    voice_index: int,
) -> List[Dict[str, int | bool]]:
    duration_value = int(beat_data.get("duration", 4))
    quarter_length = 4.0 / float(duration_value)
    start_ticks = int(beat_data.get("start_ticks", 0))
    beat_offset = (float(start_ticks) / gp.models.Duration.quarterTime) / quarter_length
    beat_index = max(0, int(round(beat_offset)))

    events = []
    for note_data in beat_data.get("notes", []):
        events.append(
            {
                "track": track_index,
                "measure": measure_index,
                "voice": voice_index,
                "beat": beat_index,
                "start_ticks": start_ticks,
                "start_quarter": round(float(start_ticks) / gp.models.Duration.quarterTime, 6),
                "string": int(note_data["string"]),
                "fret": int(note_data["fret"]),
                "duration": duration_value,
                "tied": bool(note_data.get("tied", False)),
            }
        )
    return events


def _apply_tempo_changes(measure, tempo_changes: List[Dict[str, int]]) -> None:
    if not tempo_changes:
        return

    if not measure.voices:
        measure.voices.append(gp.models.Voice(measure))

    voice = measure.voices[0]
    for tempo_change in sorted(tempo_changes, key=lambda item: item["start_ticks"]):
        beat = _find_or_create_beat_at_start(voice, int(tempo_change["start_ticks"]))
        if beat.effect is None:
            beat.effect = gp.models.BeatEffect()
        if beat.effect.mixTableChange is None:
            beat.effect.mixTableChange = gp.models.MixTableChange()
        beat.effect.mixTableChange.tempo = gp.models.MixTableItem(
            value=int(tempo_change["tempo"]),
            duration=1,
            allTracks=True,
        )


def _apply_note_effects(note, note_data: Dict[str, object]) -> None:
    if not any(
        key in note_data
        for key in (
            "palm_mute",
            "hammer_on",
            "slide",
            "vibrato",
            "ghost",
            "let_ring",
            "staccato",
            "accent",
            "heavy_accent",
            "bend",
            "harmonic",
            "trill",
            "tremolo_picking",
            "grace_fret",
            "dead",
        )
    ):
        return

    if note.effect is None:
        note.effect = gp.models.NoteEffect()

    if note_data.get("palm_mute"):
        note.effect.palmMute = True
    if note_data.get("hammer_on"):
        note.effect.hammer = True
    if note_data.get("slide"):
        note.effect.slides = [gp.SlideType.shiftSlideTo]
    if note_data.get("vibrato"):
        note.effect.vibrato = True
    if note_data.get("ghost"):
        note.effect.ghostNote = True
    if note_data.get("let_ring"):
        note.effect.letRing = True
    if note_data.get("staccato"):
        note.effect.staccato = True
    if note_data.get("accent"):
        note.effect.accentuatedNote = True
    if note_data.get("heavy_accent"):
        note.effect.heavyAccentuatedNote = True
    if note_data.get("dead"):
        note.type = gp.NoteType.dead

    if note_data.get("bend") is not None:
        bend_value = int(note_data["bend"])
        bend = gp.models.BendEffect()
        bend.type = gp.BendType.bend
        bend.value = bend_value
        bend.points = [
            gp.models.BendPoint(position=0, value=0),
            gp.models.BendPoint(position=6, value=bend_value),
        ]
        if note_data.get("bend_release"):
            bend.points.append(gp.models.BendPoint(position=12, value=0))
        note.effect.bend = bend

    harmonic = note_data.get("harmonic")
    if harmonic == "natural":
        note.effect.harmonic = gp.models.NaturalHarmonic()
    elif harmonic == "artificial":
        note.effect.harmonic = gp.models.ArtificialHarmonic()
    elif harmonic == "pinch":
        note.effect.harmonic = gp.models.PinchHarmonic()
    elif harmonic == "tap":
        note.effect.harmonic = gp.models.TappedHarmonic(fret=int(note.value))

    if note_data.get("trill"):
        trill = gp.models.TrillEffect()
        trill.fret = int(note_data["trill"])
        trill.duration = gp.models.Duration()
        trill.duration.value = int(note_data.get("trill_speed", 16))
        note.effect.trill = trill

    if note_data.get("tremolo_picking"):
        tremolo = gp.models.TremoloPickingEffect()
        tremolo.duration = gp.models.Duration()
        tremolo.duration.value = int(note_data["tremolo_picking"])
        note.effect.tremoloPicking = tremolo

    if note_data.get("grace_fret") is not None:
        grace = gp.models.GraceEffect()
        grace.fret = int(note_data["grace_fret"])
        grace.duration = int(note_data.get("grace_duration", 1))
        grace.velocity = int(note_data.get("grace_velocity", 95))
        grace.isOnBeat = bool(note_data.get("grace_on_beat", False))
        transition_map = {
            "none": gp.GraceEffectTransition.none,
            "slide": gp.GraceEffectTransition.slide,
            "bend": gp.GraceEffectTransition.bend,
            "hammer": gp.GraceEffectTransition.hammer,
        }
        grace.transition = transition_map.get(note_data.get("grace_transition", "none"), gp.GraceEffectTransition.none)
        note.effect.grace = grace


def _apply_beat_effects(beat, beat_effect_data: Dict[str, object]) -> None:
    if not beat_effect_data:
        return
    if beat.effect is None:
        beat.effect = gp.models.BeatEffect()
    if beat_effect_data.get("tap"):
        beat.effect.slapEffect = gp.SlapEffect.tapping
    elif beat_effect_data.get("slap"):
        beat.effect.slapEffect = gp.SlapEffect.slapping
    elif beat_effect_data.get("pop"):
        beat.effect.slapEffect = gp.SlapEffect.popping


def _find_or_create_beat_at_start(voice, start_ticks: int):
    for beat in voice.beats:
        if int(getattr(beat, "start", -1)) == start_ticks:
            return beat

    beat = gp.models.Beat(voice)
    beat.start = start_ticks
    beat.duration = gp.models.Duration()
    beat.duration.value = 4
    voice.beats.append(beat)
    voice.beats.sort(key=lambda beat_value: int(getattr(beat_value, "start", 0)))
    return beat
