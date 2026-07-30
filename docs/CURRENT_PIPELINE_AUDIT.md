# Current Pipeline Audit

Date: 2026-07-29

## Entry Points

- Analyzer GUI: `run_analyzer_gui.bat` starts `scripts/python/analyzer_gui.py`.
- Analyzer CLI: `scripts/python/audio_analyzer.py`.
- Lane/event generator: `scripts/python/lane_assignment.py`, called by `audio_analyzer.analyze_with_metadata`.
- Renderer scene: `scenes/main.tscn` with `scripts/godot/main.gd`.
- Beatmap loader: `scripts/beatmap_parser.gd`.
- MP4 background loader: `scripts/godot/background_mp4_backend.gd`, used by `main.gd`.
- Render wrapper: `render_video.ps1`.

## Current Analyzer Flow

1. GUI or CLI receives an audio file.
2. `audio_analyzer.isolated_rhythm_stems` runs Demucs and creates a temporary bass+drums rhythm mix.
3. `analyze_with_metadata` estimates tempo, anchor, beat grid, onset candidates, wall events, lane assignments, and hold events.
4. Outputs are written to `output/beatmap.json`, `output/beat_grid.json`, and `output/combo.srt`.
5. Temporary Demucs stems are deleted.

## Existing Input Contracts

### Audio

- GUI accepts `.wav` and `.mp3`.
- CLI default: `assets/audio/audio.mp3`.
- Local workflow default in README/GUI: `assets/audio/Iron & Ash.mp3`.

### Wall Override

`--wall-override` accepts either:

- a JSON array of wall event objects;
- a beatmap-like object with an `events` array.

The override is normalized into `wall_left` / `wall_right` events.

### Visual Config

`assets/models/wall_visual_config.json` uses schema `neon_music.wall_visual.v1`.

Important fields:

- wall geometry: `wall_height`, `wall_width_x`, `wall_length_z`;
- wall appearance: `wall_opacity`, `wall_emission_strength`, `wall_edge_glow`, segment/strip/edge emission fields;
- timing: `global_audio_offset_ms`, `visual_hit_offset_ms`;
- guidance: `safe_lane_*`, `next_cell_ring_*`;
- camera: `camera_dodge_*`;
- colors: `wall_left_color`, `wall_right_color`, `safe_lane_color`, `next_cell_ring_color`.

## Existing Output Contracts

### `output/beatmap.json`

Current schema: `neon_music.beatmap.v3`.

Top-level fields:

- `schema`
- `audio`
- `bpm`
- `beat_interval`
- `notes`
- `events`

Note fields:

- `type`: `note` or `jump`
- `time`
- `lane`
- `lanes`
- `energy_class`
- `lane_mode`
- `stem_energy`: `bass`, `drums`, `combined`
- beat annotation: `beat_index`, `beat_time`, `beat_phase`, `beat_delta`, `downbeat`

Event fields:

- `wall_left` / `wall_right`: `time`, `start`, `duration`, `end`, `lanes`, `safe_lanes`, `anticipation`, beat annotation, `selection`.
- `hold`: `time`, `start`, `duration`, `end_time`, `end`, `lane`, `side`, `foot`, beat annotation, `selection`.

Backward compatibility:

- `scripts/beatmap_parser.gd` still accepts the older note-array root format.
- Unknown top-level fields are ignored by older renderer code.

### `output/beat_grid.json`

Current schema: `neon_music.beat_grid.v1`.

Top-level fields:

- `schema`, `audio`, `sample_rate`, `duration`, `bpm`, `beat_interval`
- `tempo`
- `anchor`
- `grid_fit`
- `detected_beats`
- `beat_grid`
- `analysis`
- `generation_settings`
- `wall_generation`
- `hold_generation`
- `lane_assignment`
- counts: `note_count`, `event_count`, `wall_event_count`, `hold_count`

Beat grid entry fields:

- `index`
- `time`
- `bar_phase`
- `downbeat`

## Phase 1/2 Additive Contracts

### Choreography Config

Added to both `beatmap.json` and `beat_grid.json`:

```json
{
  "phrase_length_beats": 32,
  "subphrase_length_beats": 8,
  "manual_downbeat_offset_seconds": 0.0,
  "allow_crooked_phrase": false,
  "default_known_lead_beats": 2,
  "default_new_lead_beats": 4,
  "judgment_plane": "receptor_hit_z",
  "judgment_z": 0.0
}
```

### Phrase Grid

Added as `phrase_grid` with schema `neon_music.phrase_grid.v1`.

Important fields:

- `config`
- `beat_interval`
- `anchor_time`
- `phrase_anchor_time`
- `phrases`
- `beats`
- `sections`

Each phrase contains up to four `count8_blocks`; each block is 8 beats by default.

Each phrase-grid beat adds:

- `bar_index`
- `beat_in_bar`
- `phrase_index`
- `phrase_id`
- `phrase_beat`
- `count8_index`
- `count8_beat`
- `is_phrase_start`
- `is_subphrase_start`
- `manual_downbeat_offset_seconds`

### Movement Events

Added as `movement_events` with schema `neon_music.movement_events.v1` per event.

Fields include:

- `id`, `type`, `movement`
- `instruction_time`, `hit_time`
- `duration_beats`, `duration`
- `lead_beats`, `lead_time`
- `phrase_id`, `count8_index`, `motif_id`
- `side`, `intensity`, `difficulty`
- `is_new`, `is_mirrored`, `mirror_of`
- `cue_archetype`
- `judgment_plane`, `judgment_z`
- `preparation_pose`, `end_pose`

### Note Annotations

Existing note objects are enriched with defaults:

- `hit_time`
- `movement_event_id` when applicable
- `movement`
- `cue_archetype`
- `lead_beats`
- `instruction_time`
- `phrase_id`
- `phrase_beat`
- `count8_index`
- `is_mirrored`
- `judgment_plane`
- `judgment_z`

## Renderer Findings

- `main.gd` uses `HIT_Z := 0.0` as the authoritative receptor plane.
- Notes are spawned when `note.time - song_time <= time_to_hit`.
- `RhythmNote.sync_to_song_time` moves each note toward `z=0`.
- `_trigger_hit_event` is the single tap/hold-start visual trigger path.
- Frame-locked renders use `--render-clock=frame` and `--clock-fps`.
- MP4 backgrounds are found in `assets/images/background`, preferring `reference_fullhd.mp4` or `0727.mp4`.
- MP4 playback uses bundled FFmpeg to decode frames into `user://mp4_background_frames`.

## Render Commands

Current full wrapper:

```powershell
.\render_video.ps1 -Audio "assets/audio/Iron & Ash.mp3" -FixedFps 60 -Godot "C:\path\to\Godot.exe"
```

Short debug render pattern:

```powershell
godot --rendering-driver opengl3 --path . --write-movie output/renders/vertical_slice_debug.avi --fixed-fps 30 -- "--audio=assets/audio/Iron & Ash.mp3" "--render-clock=frame" "--clock-fps=30" "--clock-stop-after=38" "--debug-timeline"
```
