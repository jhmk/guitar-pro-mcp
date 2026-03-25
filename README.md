# Guitar Pro MCP v3.0.1

Full-featured Guitar Pro file manipulation via MCP (Model Context Protocol).

## Features

### File Formats
- **Read**: GP3, GP4, GP5, GP7, GP8, MusicXML
- **Write**: GP5, MusicXML

### Note Effects
- Bend (half, full, full_half, double, with release)
- Harmonics (natural, artificial, pinch, tap)
- Trill & Tremolo Picking
- Grace Notes
- Palm Mute, Hammer-On, Pull-Off, Slide
- Vibrato, Ghost Notes, Dead Notes
- Staccato, Accents
- Tap, Slap, Pop (bass)
- Tied Notes

### Song Structure
- Markers/Sections (Intro, Verse, Chorus, etc.)
- Repeat Start/End with alternate endings
- Tempo Changes

### Analysis
- Key detection via `music21`
- Chord analysis for a track
- Pitch range analysis for a track
- Improved `music21` score conversion with ties, dotted durations, tuplets, tempo changes, and explicit beat offsets
- Reverse conversion module for `music21` -> Guitar Pro note layouts with tuning-aware fingering
- Reverse conversion now preserves explicit start offsets, selected GP note effects, tempo changes on GP beats, and `phrase_aware` fingering segments at rests, measure boundaries, and large melodic jumps

### MusicXML
- MusicXML import keeps staff tuning / technical string-fret data from the XML layer
- `music21` is now used as a normalization pass for imported MusicXML timing when available
- Imported MusicXML note events can now carry explicit `start_ticks`, dotted values, and tuplets into the controller write path

### Convenience
- 30+ Chord shortcuts
- 6 Riff templates (metal/rock patterns)
- TAB import (standard + compact format)
- Pattern copy/paste/repeat
- Copy tracks from other GP files
- Transpose

## Installation

```bash
cd guitar-pro-mcp
uv sync
```

This release adds a `music21` dependency for symbolic music analysis tools.
The current integration now converts more GP timing detail into `music21` and includes
reverse-mapping support for timing-aware and effect-aware round-trips.

## Claude Desktop Config

```json
{
  "mcpServers": {
    "guitar-pro": {
      "command": "uv",
      "args": ["--directory", "/path/to/guitar-pro-mcp", "run", "guitar-pro-mcp"]
    }
  }
}
```

## Examples

### Create Song with Bend
```
gp_create("Solo", tempo=120, tuning="standard")
gp_add_bend(track=0, measure=0, beat=0, string=2, fret=5, bend_type="full")
gp_save("/path/to/solo.gp5")
```

### Add Section Markers
```
gp_add_marker(measure=0, title="Intro")
gp_add_marker(measure=4, title="Verse", color=[0, 255, 0])
gp_add_marker(measure=8, title="Chorus", color=[255, 0, 0])
```

### Set Repeat
```
gp_set_repeat(measure=4, repeat_type="start")
gp_set_repeat(measure=7, repeat_type="end", count=2)
```

### Export to MusicXML
```
gp_load("/path/to/song.gp5")
gp_export_musicxml("/path/to/song.xml")
```

### Analyze Key
```
gp_load("/path/to/song.gp5")
gp_analyze_key()
```

### Analyze Chords
```
gp_load("/path/to/song.gp5")
gp_analyze_chords(track_index=0)
```

### Analyze Range
```
gp_load("/path/to/song.gp5")
gp_analyze_range(track_index=0)
```

### Preview music21 Reverse Conversion
```
gp_load("/path/to/song.gp5")
gp_get_music21_note_events(track_index=0, strategy="lowest_fret")
```

Available reverse fingering strategies:
- `lowest_fret`
- `highest_string`
- `lowest_string`
- `stay_in_position`
- `phrase_aware`

`phrase_aware` now optimizes short melodic segments instead of a single unbroken voice pass.
The current segmentation heuristics reset at rests, measure boundaries, and large interval jumps, and the cost model now penalizes unrealistic stretches and large position jumps more aggressively.

### Rewrite Track via music21
```
gp_load("/path/to/song.gp5")
gp_rewrite_track_from_music21(track_index=0, strategy="stay_in_position")
```

For phrase-level optimization across a melodic line:
```
gp_load("/path/to/song.gp5")
gp_rewrite_track_from_music21(track_index=0, strategy="phrase_aware")
```

### Import MusicXML With Timing Normalization
```
gp_load("/path/to/source.musicxml")
gp_get_tracks()
```

MusicXML import now keeps explicit onset offsets when `music21` can normalize the source cleanly, so dotted figures and non-grid-aligned starts survive import more faithfully than the previous beat-count-only path.

## License

MIT
