"""
Fingering policy helpers for music21 -> Guitar Pro conversion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class StringFretPosition:
    string: int
    fret: int


@dataclass
class FingeringState:
    anchor_fret: Optional[float] = None
    last_string: Optional[int] = None
    last_fret_span: Optional[int] = None


def candidate_positions(midi_pitch: int, tuning_midi: List[int], max_fret: int = 24) -> List[StringFretPosition]:
    """Return all playable positions for a MIDI pitch under the given tuning."""
    return [
        StringFretPosition(string=index + 1, fret=midi_pitch - open_pitch)
        for index, open_pitch in enumerate(tuning_midi)
        if 0 <= midi_pitch - open_pitch <= max_fret
    ]


def choose_positions(
    midi_pitches: Iterable[int],
    tuning_midi: List[int],
    strategy: str = "lowest_fret",
    max_fret: int = 24,
    state: Optional[FingeringState] = None,
) -> Optional[List[StringFretPosition]]:
    """Choose one unique-string position per MIDI pitch."""
    ordered_pitches = sorted(int(midi_pitch) for midi_pitch in midi_pitches)
    candidate_lists = [candidate_positions(midi_pitch, tuning_midi, max_fret=max_fret) for midi_pitch in ordered_pitches]
    if any(not candidates for candidates in candidate_lists):
        return None

    best_choice: Optional[List[StringFretPosition]] = None
    best_score: Optional[tuple] = None

    def backtrack(index: int, used_strings: set[int], current: List[StringFretPosition]) -> None:
        nonlocal best_choice, best_score
        if index >= len(candidate_lists):
            score = fingering_score(current, strategy=strategy, state=state)
            if best_score is None or score < best_score:
                best_score = score
                best_choice = list(current)
            return

        for position in candidate_lists[index]:
            if position.string in used_strings:
                continue
            current.append(position)
            used_strings.add(position.string)
            backtrack(index + 1, used_strings, current)
            used_strings.remove(position.string)
            current.pop()

    backtrack(0, set(), [])
    if best_choice is None:
        return None

    update_state(best_choice, state)
    return sorted(best_choice, key=lambda position: position.string, reverse=True)


def enumerate_position_sets(
    midi_pitches: Iterable[int],
    tuning_midi: List[int],
    max_fret: int = 24,
    limit: int = 16,
) -> List[List[StringFretPosition]]:
    """Enumerate playable unique-string position sets for a note or chord."""
    ordered_pitches = sorted(int(midi_pitch) for midi_pitch in midi_pitches)
    candidate_lists = [candidate_positions(midi_pitch, tuning_midi, max_fret=max_fret) for midi_pitch in ordered_pitches]
    if any(not candidates for candidates in candidate_lists):
        return []

    results: List[List[StringFretPosition]] = []

    def backtrack(index: int, used_strings: set[int], current: List[StringFretPosition]) -> None:
        if len(results) >= limit:
            return
        if index >= len(candidate_lists):
            results.append(sorted(list(current), key=lambda position: position.string, reverse=True))
            return
        for position in candidate_lists[index]:
            if position.string in used_strings:
                continue
            current.append(position)
            used_strings.add(position.string)
            backtrack(index + 1, used_strings, current)
            used_strings.remove(position.string)
            current.pop()

    backtrack(0, set(), [])
    return results


def choose_position(
    midi_pitch: int,
    tuning_midi: List[int],
    strategy: str = "lowest_fret",
    max_fret: int = 24,
    state: Optional[FingeringState] = None,
) -> Optional[StringFretPosition]:
    """Choose one position for a single MIDI pitch."""
    positions = choose_positions(
        [midi_pitch],
        tuning_midi=tuning_midi,
        strategy=strategy,
        max_fret=max_fret,
        state=state,
    )
    if not positions:
        return None
    return positions[0]


def optimize_phrase(
    phrase_pitches: List[List[int]],
    tuning_midi: List[int],
    max_fret: int = 24,
    candidate_limit: int = 12,
) -> List[Optional[List[StringFretPosition]]]:
    """Choose fingerings across a phrase with sequence-level optimization."""
    if not phrase_pitches:
        return []

    candidate_sequences = [
        enumerate_position_sets(pitches, tuning_midi=tuning_midi, max_fret=max_fret, limit=candidate_limit)
        for pitches in phrase_pitches
    ]
    if any(not candidates for candidates in candidate_sequences):
        return [None for _ in phrase_pitches]

    costs: List[List[float]] = []
    backrefs: List[List[Optional[int]]] = []

    first_costs = [phrase_local_cost(positions) for positions in candidate_sequences[0]]
    costs.append(first_costs)
    backrefs.append([None] * len(candidate_sequences[0]))

    for event_index in range(1, len(candidate_sequences)):
        event_costs: List[float] = []
        event_backrefs: List[Optional[int]] = []
        for candidate_index, candidate in enumerate(candidate_sequences[event_index]):
            best_cost = None
            best_prev = None
            local_cost = phrase_local_cost(candidate)
            for prev_index, previous in enumerate(candidate_sequences[event_index - 1]):
                total = costs[event_index - 1][prev_index] + transition_cost(previous, candidate) + local_cost
                if best_cost is None or total < best_cost:
                    best_cost = total
                    best_prev = prev_index
            event_costs.append(float(best_cost if best_cost is not None else local_cost))
            event_backrefs.append(best_prev)
        costs.append(event_costs)
        backrefs.append(event_backrefs)

    last_index = min(range(len(costs[-1])), key=lambda index: costs[-1][index])
    solution: List[Optional[List[StringFretPosition]]] = [None] * len(candidate_sequences)
    current_index: Optional[int] = last_index
    for event_index in range(len(candidate_sequences) - 1, -1, -1):
        if current_index is None:
            break
        solution[event_index] = candidate_sequences[event_index][current_index]
        current_index = backrefs[event_index][current_index]
    return solution


def fingering_score(
    positions: List[StringFretPosition],
    strategy: str = "lowest_fret",
    state: Optional[FingeringState] = None,
) -> tuple:
    """Score a fingering choice. Lower is better."""
    frets = [position.fret for position in positions]
    strings = [position.string for position in positions]
    anchor = sum(frets) / len(frets)
    span = max(frets) - min(frets)
    string_span = max(strings) - min(strings)
    lowest_fret = min(frets)

    if strategy == "highest_string":
        return (min(strings), lowest_fret, span, anchor)
    if strategy == "lowest_string":
        return (-max(strings), lowest_fret, span, anchor)
    if strategy == "stay_in_position":
        anchor_penalty = 0.0
        string_penalty = 0
        if state is not None and state.anchor_fret is not None:
            anchor_penalty = abs(anchor - state.anchor_fret)
        if state is not None and state.last_string is not None:
            string_penalty = min(abs(string_value - state.last_string) for string_value in strings)
        return (anchor_penalty, span, string_penalty, lowest_fret, anchor)
    return (lowest_fret, span, string_span, anchor)


def phrase_local_cost(positions: List[StringFretPosition]) -> float:
    """Local cost within a phrase-aware optimizer."""
    frets = [position.fret for position in positions]
    strings = [position.string for position in positions]
    span = max(frets) - min(frets)
    open_count = sum(1 for fret in frets if fret == 0)
    average_fret = sum(frets) / len(frets)
    string_span = max(strings) - min(strings)
    stretch_penalty = max(0, span - 4) ** 2
    high_position_penalty = max(0.0, average_fret - 12.0) * 1.25
    barre_bonus = -0.75 if len(frets) > 1 and len(set(frets)) < len(frets) and min(frets) > 0 else 0.0
    return (
        (span * 1.8)
        + stretch_penalty
        + (open_count * 5.5)
        + (average_fret * 0.8)
        + (string_span * 0.4)
        + high_position_penalty
        + barre_bonus
    )


def transition_cost(previous: List[StringFretPosition], current: List[StringFretPosition]) -> float:
    """Transition cost between two fingering choices."""
    prev_anchor = sum(position.fret for position in previous) / len(previous)
    curr_anchor = sum(position.fret for position in current) / len(current)
    prev_span = max(position.fret for position in previous) - min(position.fret for position in previous)
    curr_span = max(position.fret for position in current) - min(position.fret for position in current)
    prev_strings = [position.string for position in previous]
    curr_strings = [position.string for position in current]
    anchor_shift = abs(curr_anchor - prev_anchor)
    string_shift = min(abs(curr - prev) for curr in curr_strings for prev in prev_strings)
    shift_penalty = max(0.0, anchor_shift - 5.0) ** 2
    span_change = abs(curr_span - prev_span)
    open_string_reset = 2.0 if any(position.fret == 0 for position in current) and anchor_shift > 4.0 else 0.0
    return (anchor_shift * 2.4) + shift_penalty + (string_shift * 0.75) + (span_change * 0.5) + open_string_reset


def update_state(positions: List[StringFretPosition], state: Optional[FingeringState]) -> None:
    """Update fingering state after assigning a note or chord."""
    if state is None or not positions:
        return
    state.anchor_fret = sum(position.fret for position in positions) / len(positions)
    state.last_string = positions[0].string
    state.last_fret_span = max(position.fret for position in positions) - min(position.fret for position in positions)
