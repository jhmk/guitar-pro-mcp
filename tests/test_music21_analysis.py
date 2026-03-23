import unittest

from src.controller import GuitarProController


class Music21AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.controller = GuitarProController()

    def test_analyze_key_returns_major_tonic_for_simple_progression(self):
        self.controller.create("Progression", tempo=120)
        self.controller.add_chord_by_name(0, 0, 0, "C")
        self.controller.add_chord_by_name(0, 1, 0, "F")
        self.controller.add_chord_by_name(0, 2, 0, "G")
        self.controller.add_chord_by_name(0, 3, 0, "C")

        result = self.controller.analyze_key()

        self.assertEqual(result["tonic"], "C")
        self.assertEqual(result["mode"], "major")
        self.assertEqual(result["source"], "music21")

    def test_analyze_chords_returns_named_harmony(self):
        self.controller.create("Chords", tempo=120)
        self.controller.add_chord_by_name(0, 0, 0, "Em")
        self.controller.add_chord_by_name(0, 1, 0, "C")
        self.controller.add_chord_by_name(0, 2, 0, "G")
        self.controller.add_chord_by_name(0, 3, 0, "D")

        result = self.controller.analyze_chords(0)

        names = [entry["name"] for entry in result["chords"]]
        self.assertIn("Em", names)
        self.assertIn("C", names)
        self.assertIn("G", names)
        self.assertIn("D", names)

    def test_analyze_range_returns_pitch_span(self):
        self.controller.create("Range", tempo=120)
        self.controller.add_note(0, 0, 0, 6, 0, 4)
        self.controller.add_note(0, 0, 1, 1, 12, 4)

        result = self.controller.analyze_range(0)

        self.assertEqual(result["lowest_pitch"], "E2")
        self.assertEqual(result["highest_pitch"], "E5")
        self.assertEqual(result["note_count"], 2)


if __name__ == "__main__":
    unittest.main()
