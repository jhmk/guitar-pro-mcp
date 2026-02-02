# Guitar Pro MCP Server v2.0

Fast, optimized MCP server for Guitar Pro file manipulation with Claude AI.

> **Note**: Currently, only Guitar Pro 5 (.gp5) format has been tested.

## What's New in v2.0

### 🚀 Batch Operations (10-50x faster!)
Instead of one MCP call per note, add hundreds of notes in a single call:

```python
# OLD (slow) - 50 separate calls
for note in notes:
    add_gp_note(...)

# NEW (fast) - 1 call
gp_add_notes([...50 notes...])
```

### 🎸 Built-in Tuning Presets
No more manual string configuration:
- `standard`, `drop_d`, `drop_c`, `drop_b`, `drop_a`
- `d_standard`, `c_standard`
- `open_d`, `open_g`, `dadgad`
- `standard_7`, `drop_a_7` (7-string)
- `bass_standard`, `bass_drop_d`, `bass_5_standard`

### 🎵 Chord Helpers
```python
# Power chord
gp_add_power_chord(track=0, measure=0, beat=0, root_string=6, root_fret=0)

# Any chord shape
gp_add_chord(track=0, measure=0, beat=0, frets=[0, 2, 2, 1, 0, 0])  # E major

# Palm-muted chugging
gp_add_palm_mutes(track=0, measure=0, string=6, frets=[0, 0, 0, 3, 0, 0, 0, 5])
```

### 📝 ASCII Tab Import
```python
gp_import_tab("6:0-0-3-5 5:2-2")  # Compact format
```

### 🎯 Create Complete Songs in One Call
```python
gp_create_complete(
    title="My Metal Riff",
    artist="Claude",
    tempo=140,
    tracks=[{"name": "Guitar", "tuning": "drop_d"}],
    measures=4,
    notes=[
        {"measure": 0, "beat": 0, "string": 6, "fret": 0, "palm_mute": True},
        {"measure": 0, "beat": 1, "string": 6, "fret": 0, "palm_mute": True},
        # ... more notes
    ]
)
```

## Installation

```bash
git clone https://github.com/yourusername/guitar-pro-mcp.git
cd guitar-pro-mcp
uv venv
source .venv/bin/activate  # macOS/Linux
uv pip install .
```

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
    "mcpServers": {
        "guitar-pro": {
            "type": "stdio",
            "command": "uv",
            "args": [
                "--directory",
                "/path/to/guitar-pro-mcp",
                "run",
                "-m",
                "src.server"
            ]
        }
    }
}
```

On Windows, use `%APPDATA%\Claude\claude_desktop_config.json`.

Restart Claude Desktop after editing.

## Tool Reference

### File Operations
| Tool | Description |
|------|-------------|
| `gp_load` | Load a .gp5/.gp4/.gp3 file |
| `gp_save` | Save to .gp5 format |

### Song Operations
| Tool | Description |
|------|-------------|
| `gp_create` | Create new song with one track |
| `gp_create_complete` | Create song + tracks + measures + notes in ONE call |
| `gp_info` | Get song info |
| `gp_stats` | Get statistics |
| `gp_set_properties` | Update title/artist/album/tempo |

### Track Operations
| Tool | Description |
|------|-------------|
| `gp_add_track` | Add a track with tuning preset |
| `gp_set_tuning` | Change track tuning |
| `gp_tracks` | List all tracks |

### Measure Operations
| Tool | Description |
|------|-------------|
| `gp_add_measures` | Add multiple measures at once |
| `gp_set_time_signature` | Set time signature |

### Note Operations (FAST!)
| Tool | Description |
|------|-------------|
| `gp_add_notes` | **Batch add notes** - fastest method! |
| `gp_add_note` | Add single note |
| `gp_add_power_chord` | Add power chord |
| `gp_add_chord` | Add any chord shape |
| `gp_add_palm_mutes` | Add palm-muted sequence |
| `gp_get_notes` | Get all notes from track |

### Tab Operations
| Tool | Description |
|------|-------------|
| `gp_import_tab` | Import ASCII tablature |
| `gp_get_tab` | Export track as ASCII tab |

## Note Effects

When using `gp_add_notes`, you can add effects:

```python
{
    "string": 6, "fret": 0,
    "palm_mute": True,   # P.M.
    "hammer_on": True,   # H
    "pull_off": True,    # P
    "slide": True,       # /
    "vibrato": True,     # ~
    "ghost": True,       # ()
    "dead": True         # x
}
```

## Tuning Reference

| Tuning | Strings (low to high) |
|--------|----------------------|
| `standard` | E A D G B E |
| `drop_d` | D A D G B E |
| `drop_c` | C G C F A D |
| `drop_b` | B F# B E G# C# |
| `d_standard` | D G C F A D |
| `c_standard` | C F Bb Eb G C |
| `open_d` | D A D F# A D |
| `open_g` | D G D G B D |
| `dadgad` | D A D G A D |
| `standard_7` | B E A D G B E |
| `bass_standard` | E A D G |
| `bass_drop_d` | D A D G |

## License

MIT License
