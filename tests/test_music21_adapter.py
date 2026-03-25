import unittest

import guitarpro as gp
from music21 import chord as m21chord
from music21 import duration as m21duration
from music21 import note as m21note
from music21 import stream as m21stream
from music21 import tempo as m21tempo

from src.controller import GuitarProController
from src.music21_reverse import (
    _segment_phrase_elements,
    part_to_gp_track_data,
    part_to_note_events,
    pitch_to_string_fret,
)


class Music21AdapterTests(unittest.TestCase):
    def setUp(self):
        self.controller = GuitarProController()

    def test_adapter_preserves_dotted_tuplet_and_tied_metadata(self):
        self.controller.create("Adapter", tempo=120)
        self.controller.add_note(0, 0, 0, 6, 0, 8)
        self.controller.add_note(0, 0, 1, 6, 2, 8)

        dotted_beat = self.controller.song.tracks[0].measures[0].voices[0].beats[0]
        dotted_beat.duration.isDotted = True
        dotted_beat.notes[0].type = gp.NoteType.tie

        triplet_beat = self.controller.song.tracks[0].measures[0].voices[0].beats[1]
        triplet_beat.duration.tuplet.enters = 3
        triplet_beat.duration.tuplet.times = 2

        score = self.controller._to_music21_score()
        notes = list(score.parts[0].flatten().notes)
        first_note = notes[0]
        second_note = notes[1]

        self.assertAlmostEqual(first_note.duration.quarterLength, 0.75)
        self.assertEqual(first_note.duration.dots, 1)
        self.assertIsNotNone(first_note.tie)
        self.assertAlmostEqual(second_note.duration.quarterLength, 1 / 3)
        self.assertEqual(len(second_note.duration.tuplets), 1)
        self.assertEqual(second_note.duration.tuplets[0].numberNotesActual, 3)
        self.assertEqual(second_note.duration.tuplets[0].numberNotesNormal, 2)

    def test_adapter_emits_tempo_changes_from_mix_table(self):
        self.controller.create("Tempo", tempo=120)
        self.controller.add_note(0, 0, 0, 6, 0, 4)
        self.controller.add_note(0, 0, 1, 6, 2, 4)
        self.controller.set_tempo_change(0, 0, 1, 150)

        score = self.controller._to_music21_score()
        marks = list(score.parts[0].recurse().getElementsByClass(m21tempo.MetronomeMark))
        values = [int(mark.number) for mark in marks if mark.number is not None]

        self.assertIn(150, values)

    def test_adapter_uses_explicit_beat_start_offsets(self):
        self.controller.create("Offsets", tempo=120)
        self.controller.add_notes_batch(
            [
                {"track": 0, "measure": 0, "voice": 0, "start_ticks": 0, "string": 6, "fret": 0, "duration": 8},
                {"track": 0, "measure": 0, "voice": 0, "start_ticks": 1440, "string": 5, "fret": 3, "duration": 8},
            ]
        )

        score = self.controller._to_music21_score()
        notes = list(score.parts[0].measure(1).voices[0].notes)

        self.assertAlmostEqual(notes[0].offset, 0.0)
        self.assertAlmostEqual(notes[1].offset, 1.5)

    def test_reverse_mapping_groundwork_converts_part_back_to_note_events(self):
        self.controller.create("Roundtrip", tempo=120)
        self.controller.add_note(0, 0, 0, 6, 0, 4)
        self.controller.add_note(0, 0, 1, 5, 3, 4)

        score = self.controller._to_music21_score()
        events = part_to_note_events(score.parts[0], track_index=0, tuning_midi=[64, 59, 55, 50, 45, 40])

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["string"], 6)
        self.assertEqual(events[0]["fret"], 0)
        self.assertEqual(events[1]["duration"], 4)

    def test_controller_can_rewrite_track_from_music21(self):
        self.controller.create("Rewrite", tempo=120)
        self.controller.add_note(0, 0, 0, 6, 0, 4)
        self.controller.add_note(0, 0, 1, 5, 3, 4)

        result = self.controller.rewrite_track_from_music21(0)
        notes = self.controller.get_track_notes(0)

        self.assertEqual(result["source"], "music21")
        self.assertEqual(result["notes_written"], 2)
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes[0]["string"], 6)
        self.assertEqual(notes[0]["fret"], 0)

    def test_reverse_track_data_preserves_multivoice_offsets_and_tempo(self):
        part = m21stream.Part()
        measure = m21stream.Measure(number=1)
        voice_a = m21stream.Voice(id="a")
        voice_b = m21stream.Voice(id="b")

        note_a1 = m21note.Note("E3")
        note_a1.duration = m21duration.Duration(quarterLength=1.5)
        voice_a.insert(0, note_a1)

        note_a2 = m21note.Note("G3")
        note_a2.duration = m21duration.Duration(quarterLength=0.5)
        voice_a.insert(1.5, note_a2)

        chord_b = m21chord.Chord(["C4", "E4"])
        chord_b.duration = m21duration.Duration(quarterLength=2)
        voice_b.insert(2, chord_b)

        measure.insert(0, m21tempo.MetronomeMark(number=140))
        measure.insert(0, voice_a)
        measure.insert(0, voice_b)
        part.append(measure)

        track_data = part_to_gp_track_data(part, tuning_midi=[64, 59, 55, 50, 45, 40])

        self.assertEqual(track_data["measure_count"], 1)
        self.assertEqual(len(track_data["measures"][0]["voices"]), 2)
        self.assertEqual(track_data["measures"][0]["voices"][0]["beats"][1]["start_ticks"], 1440)
        self.assertEqual(track_data["measures"][0]["voices"][1]["beats"][0]["start_ticks"], 1920)
        self.assertEqual(track_data["measures"][0]["tempo_changes"][0]["tempo"], 140)

    def test_rewrite_track_from_music21_restores_tempo_change_effect(self):
        self.controller.create("TempoRewrite", tempo=120)
        self.controller.add_note(0, 0, 0, 6, 0, 4)
        self.controller.add_note(0, 0, 1, 5, 3, 4)
        self.controller.set_tempo_change(0, 0, 1, 150)

        self.controller.rewrite_track_from_music21(0)
        beat = self.controller.song.tracks[0].measures[0].voices[0].beats[1]

        self.assertIsNotNone(beat.effect)
        self.assertIsNotNone(beat.effect.mixTableChange)
        self.assertEqual(beat.effect.mixTableChange.tempo.value, 150)

    def test_rewrite_track_from_music21_restores_note_effect_metadata(self):
        self.controller.create("EffectRewrite", tempo=120)
        self.controller.add_notes_batch(
            [
                {
                    "track": 0,
                    "measure": 0,
                    "beat": 0,
                    "string": 6,
                    "fret": 3,
                    "duration": 4,
                    "palm_mute": True,
                    "vibrato": True,
                    "bend": "half",
                    "grace_fret": 2,
                    "grace_transition": "slide",
                    "staccato": True,
                    "accent": True,
                }
            ]
        )

        self.controller.rewrite_track_from_music21(0)
        note = self.controller.song.tracks[0].measures[0].voices[0].beats[0].notes[0]

        self.assertTrue(note.effect.palmMute)
        self.assertTrue(note.effect.vibrato)
        self.assertTrue(note.effect.staccato)
        self.assertTrue(note.effect.accentuatedNote)
        self.assertIsNotNone(note.effect.bend)
        self.assertEqual(note.effect.bend.value, 50)
        self.assertIsNotNone(note.effect.grace)
        self.assertEqual(note.effect.grace.fret, 2)

    def test_pitch_to_string_fret_prefers_lowest_fret(self):
        position = pitch_to_string_fret(52, tuning_midi=[64, 59, 55, 50, 45, 40])

        self.assertIsNotNone(position)
        self.assertEqual(position.string, 4)
        self.assertEqual(position.fret, 2)

    def test_stay_in_position_prefers_stable_hand_position(self):
        part = m21stream.Part()
        measure = m21stream.Measure(number=1)
        note_a = m21note.Note()
        note_a.pitch.midi = 52
        note_a.duration = m21duration.Duration(quarterLength=1)
        note_b = m21note.Note()
        note_b.pitch.midi = 52
        note_b.duration = m21duration.Duration(quarterLength=1)
        note_c = m21note.Note()
        note_c.pitch.midi = 55
        note_c.duration = m21duration.Duration(quarterLength=1)
        measure.insert(0, note_a)
        measure.insert(1, note_b)
        measure.insert(2, note_c)
        part.append(measure)

        lowest = part_to_note_events(part, tuning_midi=[64, 59, 55, 50, 45, 40], strategy="lowest_fret")
        stable = part_to_note_events(part, tuning_midi=[64, 59, 55, 50, 45, 40], strategy="stay_in_position")

        self.assertEqual(lowest[0]["string"], 4)
        self.assertEqual(lowest[1]["string"], 4)
        self.assertEqual(stable[0]["string"], 4)
        self.assertEqual(stable[1]["string"], 4)
        self.assertEqual(stable[2]["string"], 3)

    def test_rewrite_track_from_music21_supports_stay_in_position_strategy(self):
        self.controller.create("Stable", tempo=120)
        self.controller.add_note(0, 0, 0, 4, 2, 4)
        self.controller.add_note(0, 0, 1, 4, 2, 4)
        self.controller.add_note(0, 0, 2, 3, 0, 4)

        result = self.controller.rewrite_track_from_music21(0, strategy="stay_in_position")
        notes = self.controller.get_track_notes(0)

        self.assertEqual(result["source"], "music21")
        self.assertEqual(len(notes), 3)
        self.assertEqual(notes[0]["string"], 4)
        self.assertEqual(notes[1]["string"], 4)

    def test_phrase_aware_prefers_positioned_phrase_over_open_strings(self):
        part = m21stream.Part()
        measure = m21stream.Measure(number=1)
        for offset, midi in [(0, 59), (1, 64), (2, 59)]:
            n = m21note.Note()
            n.pitch.midi = midi
            n.duration = m21duration.Duration(quarterLength=1)
            measure.insert(offset, n)
        part.append(measure)

        lowest = part_to_note_events(part, tuning_midi=[64, 59, 55, 50, 45, 40], strategy="lowest_fret")
        phrase = part_to_note_events(part, tuning_midi=[64, 59, 55, 50, 45, 40], strategy="phrase_aware")

        self.assertEqual([item["string"] for item in lowest], [2, 1, 2])
        self.assertEqual([item["fret"] for item in phrase], [4, 5, 4])
        self.assertEqual([item["string"] for item in phrase], [3, 2, 3])

    def test_phrase_segmentation_breaks_on_rests(self):
        voice = m21stream.Voice(id="seg-rests")

        first = m21note.Note("B3")
        first.duration = m21duration.Duration(quarterLength=1)
        voice.insert(0, first)

        pause = m21note.Rest()
        pause.duration = m21duration.Duration(quarterLength=1)
        voice.insert(1, pause)

        second = m21note.Note("E4")
        second.duration = m21duration.Duration(quarterLength=1)
        voice.insert(2, second)

        third = m21note.Note("F4")
        third.duration = m21duration.Duration(quarterLength=1)
        voice.insert(3, third)

        segments = _segment_phrase_elements(list(voice.notesAndRests))

        self.assertEqual(len(segments), 2)
        self.assertEqual([element.pitch.midi for element in segments[0]], [59])
        self.assertEqual([element.pitch.midi for element in segments[1]], [64, 65])

    def test_phrase_segmentation_breaks_on_large_interval_jumps(self):
        voice = m21stream.Voice(id="seg-jumps")
        for offset, pitch_name in [(0, "E3"), (1, "E4"), (2, "F4")]:
            element = m21note.Note(pitch_name)
            element.duration = m21duration.Duration(quarterLength=1)
            voice.insert(offset, element)

        segments = _segment_phrase_elements(list(voice.notesAndRests))

        self.assertEqual(len(segments), 2)
        self.assertEqual([element.pitch.midi for element in segments[0]], [52])
        self.assertEqual([element.pitch.midi for element in segments[1]], [64, 65])


if __name__ == "__main__":
    unittest.main()
