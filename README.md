# Guitar Pro MCP v3.0

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

## License

MIT
