"""
music21 adapter helpers for Guitar Pro MCP.

This module provides a higher-fidelity one-way conversion from a
PyGuitarPro song to a music21 score for symbolic analysis.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import guitarpro as gp
from music21 import chord, duration, instrument, metadata, meter, note, pitch, stream, tempo, tie


QUARTER_TIME = gp.models.Duration.quarterTime


def gp_duration_to_quarter_length(gp_duration: Optional[int]) -> float:
    """Convert a Guitar Pro duration value into a quarter length."""
    if not gp_duration:
        return 1.0
    return 4.0 / float(gp_duration)


def song_to_score(song) -> stream.Score:
    """Convert a PyGuitarPro song into a music21 score."""
    score = stream.Score(id="guitar-pro-mcp")
    score.metadata = metadata.Metadata()
    score.metadata.title = getattr(song, "title", "") or "Untitled"
    score.metadata.composer = getattr(song, "artist", "") or ""

    if getattr(song, "tempo", None):
        score.insert(0, tempo.MetronomeMark(number=song.tempo))

    for track_index, track in enumerate(song.tracks):
        part = _track_to_part(song, track, track_index)
        score.append(part)

    return score

def _track_to_part(song, track, track_index: int) -> stream.Part:
    part = stream.Part(id=f"P{track_index + 1}")
    part.partName = track.name or f"Track {track_index + 1}"
    part.partAbbreviation = part.partName

    midi_program = max(0, int(getattr(track.channel, "instrument", 24)))
    try:
        part.insert(0, instrument.instrumentFromMidiProgram(midi_program))
    except Exception:
        part.insert(0, instrument.Guitar())

    measure_headers = getattr(song, "measureHeaders", [])
    for measure_index, measure in enumerate(track.measures):
        header = measure_headers[measure_index] if measure_index < len(measure_headers) else None
        part.append(_measure_to_stream(measure, header, track, measure_index, include_tempi=track_index == 0))

    return part


def _measure_to_stream(measure, header, track, measure_index: int, include_tempi: bool) -> stream.Measure:
    measure_stream = stream.Measure(number=measure_index + 1)
    measure_length = 4.0

    if header and getattr(header, "timeSignature", None):
        numerator = header.timeSignature.numerator
        denominator = header.timeSignature.denominator.value
        time_signature = meter.TimeSignature(f"{numerator}/{denominator}")
        measure_stream.timeSignature = time_signature
        measure_length = float(time_signature.barDuration.quarterLength)

    tempo_marks: Dict[float, tempo.MetronomeMark] = {}
    for voice_index, voice_data in enumerate(measure.voices):
        voice_stream = _voice_to_stream(
            voice_data,
            track,
            measure_length=measure_length,
            voice_index=voice_index,
            tempo_marks=tempo_marks if include_tempi else None,
        )
        if len(voice_stream):
            measure_stream.insert(0, voice_stream)

    if include_tempi:
        for offset, metronome_mark in sorted(tempo_marks.items(), key=lambda item: item[0]):
            measure_stream.insert(offset, metronome_mark)

    if not measure.voices:
        rest = note.Rest()
        rest.duration = duration.Duration(quarterLength=measure_length)
        measure_stream.insert(0, rest)

    return measure_stream


def _voice_to_stream(voice_data, track, measure_length: float, voice_index: int, tempo_marks=None) -> stream.Voice:
    voice_stream = stream.Voice(id=f"voice-{voice_index}")
    current_offset = 0.0

    for beat in sorted(voice_data.beats, key=lambda current_beat: int(getattr(current_beat, "start", 0))):
        beat_offset = float(getattr(beat, "start", 0)) / QUARTER_TIME
        if beat_offset > current_offset:
            rest = note.Rest()
            rest.duration = duration.Duration(quarterLength=beat_offset - current_offset)
            voice_stream.insert(current_offset, rest)
            current_offset = beat_offset

        element = _beat_to_element(beat, track)
        if tempo_marks is not None:
            tempo_mark = _extract_tempo_mark(beat)
            if tempo_mark is not None:
                tempo_marks.setdefault(beat_offset, tempo_mark)
        voice_stream.insert(beat_offset, element)
        current_offset = max(current_offset, beat_offset + float(element.duration.quarterLength))

    if current_offset < measure_length:
        rest = note.Rest()
        rest.duration = duration.Duration(quarterLength=measure_length - current_offset)
        voice_stream.insert(current_offset, rest)

    return voice_stream


def _beat_to_element(beat, track):
    beat_duration = _gp_duration_to_duration(getattr(beat, "duration", None))
    if not beat.notes:
        rest = note.Rest()
        rest.duration = beat_duration
        rest._gp_metadata = {
            "start_ticks": int(getattr(beat, "start", 0)),
            "beat_effect": _extract_beat_metadata(beat),
            "note_effects": [],
        }
        return rest

    ordered_notes = sorted(beat.notes, key=lambda note_data: _note_to_midi(note_data, track))
    pitches = [_note_to_pitch(note_data, track) for note_data in ordered_notes]
    if len(pitches) == 1:
        element = note.Note(pitches[0])
        _apply_note_metadata(element, ordered_notes[0])
    else:
        element = chord.Chord(pitches)
        _apply_chord_metadata(element, ordered_notes)

    element.duration = beat_duration
    element._gp_metadata = {
        "start_ticks": int(getattr(beat, "start", 0)),
        "beat_effect": _extract_beat_metadata(beat),
        "note_effects": [_extract_note_metadata(note_data) for note_data in ordered_notes],
    }
    return element


def _gp_duration_to_duration(gp_duration_obj) -> duration.Duration:
    if gp_duration_obj is None:
        return duration.Duration(quarterLength=1.0)

    quarter_length = float(gp_duration_obj.time) / QUARTER_TIME
    result = duration.Duration(quarterLength=quarter_length)

    if getattr(gp_duration_obj, "isDotted", False):
        result.dots = 1

    tuplet_data = getattr(gp_duration_obj, "tuplet", None)
    if tuplet_data and (tuplet_data.enters, tuplet_data.times) != (1, 1):
        try:
            result.appendTuplet(duration.Tuplet(tuplet_data.enters, tuplet_data.times))
        except Exception:
            pass

    return result


def _apply_note_metadata(target, note_data) -> None:
    if note_data.type == gp.NoteType.tie:
        target.tie = tie.Tie("continue")


def _apply_chord_metadata(target: chord.Chord, notes: Iterable) -> None:
    if notes and all(note_data.type == gp.NoteType.tie for note_data in notes):
        target.tie = tie.Tie("continue")


def _extract_tempo_mark(beat) -> Optional[tempo.MetronomeMark]:
    effect = getattr(beat, "effect", None)
    mix_change = getattr(effect, "mixTableChange", None) if effect is not None else None
    tempo_item = getattr(mix_change, "tempo", None) if mix_change is not None else None
    if tempo_item is None:
        return None

    value = getattr(tempo_item, "value", None)
    if value is None:
        return None
    return tempo.MetronomeMark(number=int(value))


def _extract_beat_metadata(beat) -> Dict[str, object]:
    metadata: Dict[str, object] = {}
    effect = getattr(beat, "effect", None)
    if effect is None:
        return metadata

    slap_effect = getattr(effect, "slapEffect", None)
    if slap_effect == gp.SlapEffect.tapping:
        metadata["tap"] = True
    elif slap_effect == gp.SlapEffect.slapping:
        metadata["slap"] = True
    elif slap_effect == gp.SlapEffect.popping:
        metadata["pop"] = True
    return metadata


def _extract_note_metadata(note_data) -> Dict[str, object]:
    metadata: Dict[str, object] = {
        "midi": _note_to_midi(note_data, note_data.beat.voice.measure.track),
    }
    effect = getattr(note_data, "effect", None)

    if note_data.type == gp.NoteType.tie:
        metadata["tied"] = True
    if note_data.type == gp.NoteType.dead:
        metadata["dead"] = True

    if effect is None:
        return metadata

    if getattr(effect, "palmMute", False):
        metadata["palm_mute"] = True
    if getattr(effect, "hammer", False):
        metadata["hammer_on"] = True
    if getattr(effect, "vibrato", False):
        metadata["vibrato"] = True
    if getattr(effect, "ghostNote", False):
        metadata["ghost"] = True
    if getattr(effect, "letRing", False):
        metadata["let_ring"] = True
    if getattr(effect, "staccato", False):
        metadata["staccato"] = True
    if getattr(effect, "accentuatedNote", False):
        metadata["accent"] = True
    if getattr(effect, "heavyAccentuatedNote", False):
        metadata["heavy_accent"] = True
    if getattr(effect, "slides", None):
        metadata["slide"] = True

    bend = getattr(effect, "bend", None)
    if bend is not None and getattr(bend, "value", None) is not None:
        metadata["bend"] = int(bend.value)
        points = list(getattr(bend, "points", []) or [])
        if points and getattr(points[-1], "value", None) == 0 and len(points) > 2:
            metadata["bend_release"] = True

    harmonic = getattr(effect, "harmonic", None)
    if harmonic is not None:
        harmonic_map = {
            gp.NaturalHarmonic: "natural",
            gp.ArtificialHarmonic: "artificial",
            gp.PinchHarmonic: "pinch",
            gp.TappedHarmonic: "tap",
        }
        for harmonic_type, harmonic_name in harmonic_map.items():
            if isinstance(harmonic, harmonic_type):
                metadata["harmonic"] = harmonic_name
                break

    trill = getattr(effect, "trill", None)
    if trill is not None:
        metadata["trill"] = int(getattr(trill, "fret", 0))
        trill_duration = getattr(trill, "duration", None)
        if trill_duration is not None and getattr(trill_duration, "value", None) is not None:
            metadata["trill_speed"] = int(trill_duration.value)

    tremolo = getattr(effect, "tremoloPicking", None)
    if tremolo is not None:
        tremolo_duration = getattr(tremolo, "duration", None)
        if tremolo_duration is not None and getattr(tremolo_duration, "value", None) is not None:
            metadata["tremolo_picking"] = int(tremolo_duration.value)

    grace = getattr(effect, "grace", None)
    if grace is not None:
        metadata["grace_fret"] = int(getattr(grace, "fret", 0))
        metadata["grace_duration"] = int(getattr(grace, "duration", 1))
        metadata["grace_velocity"] = int(getattr(grace, "velocity", 95))
        metadata["grace_on_beat"] = bool(getattr(grace, "isOnBeat", False))
        transition_map = {
            gp.GraceEffectTransition.none: "none",
            gp.GraceEffectTransition.slide: "slide",
            gp.GraceEffectTransition.bend: "bend",
            gp.GraceEffectTransition.hammer: "hammer",
        }
        metadata["grace_transition"] = transition_map.get(getattr(grace, "transition", None), "none")

    return metadata


def _note_to_pitch(note_data, track) -> pitch.Pitch:
    midi = _note_to_midi(note_data, track)
    result = pitch.Pitch()
    result.midi = midi
    return result


def _note_to_midi(note_data, track) -> int:
    strings_by_number: Dict[int, int] = {
        string.number: string.value for string in sorted(track.strings, key=lambda s: s.number)
    }
    open_string_midi = strings_by_number.get(note_data.string, 60)
    return open_string_midi + int(note_data.value)
