"""
music21-backed analysis helpers for Guitar Pro MCP.
"""

from __future__ import annotations

from typing import Any, Dict, List

from music21 import chord, harmony


def analyze_key(score) -> Dict[str, Any]:
    """Estimate the score key using music21's key analyzer."""
    key_result = score.analyze("key")
    result: Dict[str, Any] = {
        "tonic": key_result.tonic.name,
        "mode": key_result.mode,
        "source": "music21",
    }

    correlation = getattr(key_result, "correlationCoefficient", None)
    if correlation is not None:
        result["correlation"] = round(float(correlation), 6)

    alternates: List[str] = []
    relative = getattr(key_result, "relative", None)
    if relative is not None:
        alternates.append(f"{relative.tonic.name} {relative.mode}")
    parallel = getattr(key_result, "parallel", None)
    if parallel is not None:
        label = f"{parallel.tonic.name} {parallel.mode}"
        if label not in alternates:
            alternates.append(label)
    if alternates:
        result["alternate"] = alternates

    return result


def analyze_chords(score, track_index: int = 0) -> Dict[str, Any]:
    """Detect chord content in a single track via chordify."""
    part = score.parts[track_index]
    chords: List[Dict[str, Any]] = []

    for event in part.chordify().recurse().getElementsByClass(chord.Chord):
        if not event.pitches:
            continue
        label = _chord_label(event)
        if not label:
            continue
        chords.append(
            {
                "measure": max(0, (event.measureNumber or 1) - 1),
                "beat": _beat_to_zero_based(event.beat),
                "name": label,
            }
        )

    return {"track": track_index, "chords": _dedupe_chords(chords), "source": "music21"}


def analyze_range(score, track_index: int = 0) -> Dict[str, Any]:
    """Return pitch range information for a track."""
    part = score.parts[track_index]
    pitches = [pitch for n in part.flatten().notes for pitch in n.pitches]
    if not pitches:
        return {
            "track": track_index,
            "lowest_pitch": None,
            "highest_pitch": None,
            "note_count": 0,
            "source": "music21",
        }

    lowest = min(pitches, key=lambda value: value.midi)
    highest = max(pitches, key=lambda value: value.midi)
    return {
        "track": track_index,
        "lowest_pitch": lowest.nameWithOctave,
        "highest_pitch": highest.nameWithOctave,
        "note_count": len(pitches),
        "lowest_midi": lowest.midi,
        "highest_midi": highest.midi,
        "source": "music21",
    }


def _chord_label(chord_event: chord.Chord) -> str:
    try:
        symbol = harmony.chordSymbolFromChord(chord_event)
        if symbol.figure:
            return symbol.figure
    except Exception:
        pass

    if chord_event.commonName and chord_event.commonName != "chord":
        return chord_event.commonName
    return chord_event.pitchedCommonName or ""


def _beat_to_zero_based(beat_value: Any) -> float:
    if beat_value is None:
        return 0.0
    return round(max(0.0, float(beat_value) - 1.0), 3)


def _dedupe_chords(chords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    last = None
    for chord_data in chords:
        current = (chord_data["measure"], chord_data["beat"], chord_data["name"])
        if current == last:
            continue
        deduped.append(chord_data)
        last = current
    return deduped
