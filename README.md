# Guitar Pro MCP Server v2.2

Fast, optimized MCP server for Guitar Pro file manipulation with Claude AI.

## What's New in v2.2

### 🎸 TAB BULK IMPORT
Import complete tablature in one call:
```python
gp_import_tab("""
e|--0--3--5--3--0--|
B|-----------------|
G|-----------------|
D|-----------------|
A|-----------------|
E|--0--0--0--0--0--|
""")

# Or compact format:
gp_import_tab("6:0-0-3-5 5:2-2-0")
```

### 🔄 PATTERN COPY/REPEAT
```python
# Copy measures 0-1 and repeat 4 times starting at measure 2
gp_repeat_pattern(track=0, source_start=0, source_end=1, dest_start=2, times=4)
```

### 📁 COPY FROM EXISTING FILE
```python
gp_copy_track_from_file("/path/to/original.gp5", source_track_index=0, dest_track_name="Guitar Copy")
```

### 🎵 CHORD SHORTCUTS
```python
gp_add_chord(0, 0, 0, chord_name="E")  # E major
gp_add_chord(0, 0, 1, chord_name="Am") # A minor
gp_add_chord_progression(0, 0, ["E", "A", "B", "E"])
```

Available chords: E, Em, A, Am, D, Dm, G, C, F, B, Bm, E5, A5, D5, G5, E7, A7, Em7, Am7, Asus2, Asus4, Dsus2, Dsus4

### 🎼 RIFF TEMPLATES
```python
gp_add_riff_template(track=0, measure=0, template_name="chug_basic", root_fret=0, repeat=4)
```

Templates: `chug_basic`, `chug_gallop`, `chug_breakdown`, `power_quarters`, `djent_basic`, `thrash_pick`

### 🎹 MULTI-TRACK BATCH
```python
gp_add_notes_multi_track({
    0: [guitar_notes],
    1: [bass_notes]
})
```

### ⬆️ TRANSPOSE
```python
gp_transpose(track_index=0, semitones=-2)  # Down 2 semitones
```

## Tuning Presets

| Tuning | Strings |
|--------|---------|
| `standard` | E A D G B E |
| `drop_d` | D A D G B E |
| `drop_c` | C G C F A D |
| `drop_b` | B F# B E G# C# |
| `d_standard` | D G C F A D |
| `c_standard` | C F Bb Eb G C |
| `standard_7` | B E A D G B E |
| `bass_standard` | E A D G |
| `bass_drop_d` | D A D G |
| `bass_drop_c` | C G C F |

## Installation

```bash
git clone https://github.com/yourusername/guitar-pro-mcp.git
cd guitar-pro-mcp
uv venv
source .venv/bin/activate
uv pip install .
```

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

## Tool Reference

### File Operations
| Tool | Description |
|------|-------------|
| `gp_load` | Load .gp5/.gp4/.gp3 file |
| `gp_save` | Save to .gp5 |

### Song Creation
| Tool | Description |
|------|-------------|
| `gp_create` | New song with one track |
| `gp_create_complete` | Complete song in ONE call |

### Tab Import (NEW!)
| Tool | Description |
|------|-------------|
| `gp_import_tab` | **Import ASCII tab** - fastest way! |

### Pattern Operations (NEW!)
| Tool | Description |
|------|-------------|
| `gp_copy_measures` | Copy to clipboard |
| `gp_paste_measures` | Paste with repeat |
| `gp_repeat_pattern` | Copy + repeat in one call |
| `gp_copy_track_from_file` | Copy from another .gp5 |

### Chord Operations (NEW!)
| Tool | Description |
|------|-------------|
| `gp_add_chord` | Add chord by name or frets |
| `gp_add_power_chord` | Add power chord |
| `gp_add_chord_progression` | Add chord sequence |
| `gp_list_chords` | List available chords |

### Riff Templates (NEW!)
| Tool | Description |
|------|-------------|
| `gp_list_riff_templates` | List templates |
| `gp_add_riff_template` | Add template |

### Note Operations
| Tool | Description |
|------|-------------|
| `gp_add_notes` | Batch add notes |
| `gp_add_notes_multi_track` | Add to multiple tracks |
| `gp_add_palm_mutes` | Palm-muted sequence |

### Transpose (NEW!)
| Tool | Description |
|------|-------------|
| `gp_transpose` | Transpose track |

## IMPORTANT: Beat Values

Beat values must be **integers** (0, 1, 2, 3...), not floats!

```python
# CORRECT
{"beat": 0, "string": 6, "fret": 0}
{"beat": 1, "string": 6, "fret": 3}

# WRONG - will cause errors
{"beat": 0.5, "string": 6, "fret": 0}
```

## License

MIT License
