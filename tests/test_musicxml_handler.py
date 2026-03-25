import unittest
from pathlib import Path

from src.controller import GuitarProController
from src.musicxml_handler import import_musicxml


FIXTURES = Path(__file__).parent / "fixtures"


class MusicXMLHandlerTests(unittest.TestCase):
    def test_import_musicxml_normalizes_timing_with_music21(self):
        data = import_musicxml(str(FIXTURES / "dotted_phrase.musicxml"))

        self.assertEqual(data["title"], "Dotted Phrase")
        self.assertEqual(data["tempo"], 132)
        self.assertEqual(len(data["tracks"]), 1)
        self.assertEqual(len(data["tracks"][0]["notes"]), 2)
        self.assertTrue(data["tracks"][0]["notes"][0]["is_dotted"])
        self.assertEqual(data["tracks"][0]["notes"][0]["start_ticks"], 0)
        self.assertEqual(data["tracks"][0]["notes"][1]["start_ticks"], 1440)
        self.assertEqual(data["tracks"][0]["notes"][1]["duration"], 8)

    def test_import_musicxml_preserves_fixture_tuning(self):
        data = import_musicxml(str(FIXTURES / "seven_string.musicxml"))

        self.assertEqual(data["tracks"][0]["name"], "Seven String")
        self.assertEqual(len(data["tracks"][0]["tuning"]), 7)
        self.assertEqual(data["tracks"][0]["tuning"][-1], 35)
        self.assertEqual(data["tracks"][0]["notes"][0]["string"], 7)
        self.assertEqual(data["tracks"][0]["notes"][0]["fret"], 0)

    def test_controller_load_musicxml_uses_explicit_start_ticks(self):
        controller = GuitarProController()
        controller.load_musicxml(str(FIXTURES / "dotted_phrase.musicxml"))

        beats = controller.song.tracks[0].measures[0].voices[0].beats

        self.assertEqual([beat.start for beat in beats], [0, 1440])


if __name__ == "__main__":
    unittest.main()
