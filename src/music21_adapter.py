"""
music21 adapter helpers for Guitar Pro MCP.

This module provides a one-way conversion from a PyGuitarPro song to a
music21 score so the server can expose symbolic analysis tools without
changing its core GP-centric editing model.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from music21 import chord, duration, instrument, metadata, meter, note, pitch, stream, tempo


def gp_duration_to_quarter_length(gp_duration: Optional[int]) -> float:
    """Convert Guitar Pro duration values into music21 quarter lengths."""
    if not gp_duration:
        return 1.0
    return 4.0 / float(gp_duration)


def song_to_score(song) -> stream.Score:
    """Convert a PyGuitarPro song into a music21 score."""
    score = stream.Score(id="guitar-pro-mcp")
    score.metadata = metadata.Metadata()
    score.metadata.title = getattr(song, "title", "") or "Untitled"
    score.metadata.composer = getattr(song, "artist", "") or ""

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

    if getattr(song, "tempo", None):
        part.insert(0, tempo.MetronomeMark(number=song.tempo))

    measure_headers = getattr(song, "measureHeaders", [])
    for measure_index, measure in enumerate(track.measures):
        header = measure_headers[measure_index] if measure_index < len(measure_headers) else None
        part.append(_measure_to_stream(measure, header, track, measure_index))

    return part


def _measure_to_stream(measure, header, track, measure_index: int) -> stream.Measure:
    measure_stream = stream.Measure(number=measure_index + 1)
    if header and getattr(header, "timeSignature", None):
        numerator = header.timeSignature.numerator
        denominator = header.timeSignature.denominator.value
        measure_stream.timeSignature = meter.TimeSignature(f"{numerator}/{denominator}")

    for voice_index, voice_data in enumerate(measure.voices):
        voice_stream = stream.Voice(id=f"voice-{voice_index}")
        current_offset = 0.0
        for beat in voice_data.beats:
            element = _beat_to_element(beat, track)
            voice_stream.insert(current_offset, element)
            current_offset += element.duration.quarterLength
        measure_stream.insert(0, voice_stream)

    if not measure.voices:
        rest = note.Rest()
        rest.duration = duration.Duration(1.0)
        measure_stream.insert(0, rest)

    return measure_stream


def _beat_to_element(beat, track):
    quarter_length = gp_duration_to_quarter_length(
        beat.duration.value if getattr(beat, "duration", None) else None
    )
    if not beat.notes:
        rest = note.Rest()
        rest.duration = duration.Duration(quarterLength=quarter_length)
        return rest

    pitches = [_note_to_pitch(note_data, track) for note_data in beat.notes]
    if len(pitches) == 1:
        element = note.Note(pitches[0])
    else:
        element = chord.Chord(pitches)
    element.duration = duration.Duration(quarterLength=quarter_length)
    return element


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
