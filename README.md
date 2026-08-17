# Neon Footstep Renderer

This Godot project renders a four-lane neon rhythm video. The analyzer and render script accept the same audio input; the canonical local track path for this workflow is `assets/audio/audio.wav`. Audio media is not stored in Git, so place the source WAV at that path after cloning or select another WAV/MP3 in the analyzer.

## Dependencies

Install the analyzer dependencies before generating a beatmap:

```powershell
python -m pip install -r requirements.txt
```

The analyzer runs Demucs with the `htdemucs` model and `--demucs-device auto` by default, trying PyTorch/CUDA first and falling back to CPU if CUDA separation fails. It isolates `bass.wav` and `drums.wav`, builds a temporary bass+drums rhythm mix for analysis, writes the JSON/SRT files under `output/`, then permanently removes its temporary separation directory and every generated stem. Use `--demucs-device cpu` to skip CUDA probing.

The current analyzer also performs music-aware choreography analysis: optional
neural beat/downbeat/meter tracking, multi-band accents, subdivision groove,
energy/harmony/timbre changes, bar-aligned sections, drops/breaks/fills, and
per-phrase movement targets. The full design and research sources are in
`docs/MUSIC_CHOREOGRAPHY_ANALYZER_V5.md`. Install the optional neural backend
with `python -m pip install -r requirements-advanced.txt`; the default signal
path remains available with `--no-neural-meter`.

V4 also shapes every complete 32-beat phrase as four readable 8-count blocks:
`SETUP -> DEVELOP -> LIFT -> PAYOFF`. The generator develops one primary
movement axis at a time (intensity, density, level, travel, or upper body),
uses impact-rebuild curves for drops, and release curves for recovery/outro.
Run `generate_choreography_v4.py` without `--profile` for the normal dynamic
profile; `--profile warmup_first` is the explicit teaching-mode alternative.

Compound choreography is projected as synchronized component cues rather than
one ambiguous icon. `SYNC_STEP_PUNCH_*` pairs a same-side step and punch on the
same beat; the harder `CROSS_STEP_PUNCH_*` is allowed only after a simple sync
pattern has appeared earlier in the phrase. `DOUBLE_FOOT_PULSE` emits two
grounded foot-pad cues and is not treated as a jump. Repeated verse/chorus/drop
sections use motif memory to recall a recognizable hook while penalizing exact
phrase copies, and transition scoring accounts for stance, level, weight,
impact, and compound-pattern changes.

Two music-reactive dynamics are layered on top of that grammar. Body
counterpoint maps kick/low accents toward grounded footwork and snare/high
accents toward hand or upper-body cues, rewarding readable alternation rather
than extra notes. `PICKUP_TO_DROP` may replace the final 8-count before a
detected drop with two hand calls and a grounded double-foot response; the
high-impact payoff remains on the following drop.

## Analyzer Workflow

1. Install Python 3.10+ dependencies if needed: `python -m pip install -r requirements.txt`.
2. Open the analyzer GUI:

   ```powershell
   .\run_analyzer_gui.bat
   ```

3. Choose an audio file and output path on **Track & Dance**, select the dance difficulty/layout, then click **Generate choreography** in the fixed action bar. Obstacles and renderer-only visual tuning live on separate tabs. The GUI writes the canonical `output/neon_track.json`, held numeric `output/combo.srt`, and sparse status `output/feedback.srt`; **Validate current track** validates the path currently selected in the GUI.

The CLI uses the same pipeline and still defaults to `Active` so the existing workflow keeps working:

```powershell
python scripts/python/audio_analyzer.py --audio "assets/audio/audio.wav"
```

Onset detection is rhythm-stem focused: Demucs separates bass and drums, the analyzer blends bass low-band Mel onset energy, drum onset energy, and RMS flux, then uses `scipy.signal.find_peaks` to pick deterministic peak candidates before backtracking frames to local energy minima. Peak energy classification drives choreography: normal beats prefer inner lanes `1`/`2`, heavy bass/drum hits prefer wide lanes `0`/`3`, and massive combined energy spikes export as `jump` notes with `lanes: [0, 3]`. The existing profile `min_time_between_notes` filter still controls final note density after SciPy peak candidates are found.

Optional warm-up and difficulty controls:

```powershell
python scripts/python/audio_analyzer.py --audio "assets/audio/audio.wav" --difficulty Calm --ramp-duration 32 --ramp-strength 0.7 --max-same-lane-run 2 --max-same-side-run 4
```

The analyzer creates one canonical `output/neon_track.json` and two CapCut tracks. `combo.srt` contains only the cumulative number; every entry lasts until the next distinct hit, and simultaneous targets are collapsed into one score update. `feedback.srt` contains long-lived reference-shaped tiers such as `GREAT`, `PERFECT`, and `UNSTOPPABLE`. The track embeds the `beatmap` and `beat_grid` payloads used by Godot and diagnostics. The embedded beatmap keeps separate `notes` and `events` arrays; the loader still accepts older standalone files only for explicit compatibility workflows.

### CapCut combo overlay

1. Import the rendered video, then use **Captions → Add captions → Import file** and select `output/combo.srt`.
2. Select one numeric caption, place it in the upper-right safe area, choose a wide techno font, white fill, a soft dark shadow, and enable **Apply to all captions**.
3. Add one ordinary Text layer reading `COMBO` directly below the number and stretch it across the complete video. Keeping this static label outside SRT allows a much smaller font and wider tracking.
4. Import `output/feedback.srt` as the second caption layer. Place it below and slightly left of the score, use the level accent color, dark semi-transparent plate, thin outline, and a short entrance animation. Apply the style to all feedback captions.
5. Do not add an exit animation to every numeric caption: the adjacent SRT intervals already create a clean score replacement without a blank frame or flashing.

Wall events are generated automatically for any audio input from deterministic phrase/downbeat candidates that stay low in onset density and RMS energy across preparation, wall, and recovery rest windows. They alternate `wall_left` and `wall_right`, include `start`, `duration`, blocked `lanes`, mirrored `safe_lanes`, and `anticipation`, and ordinary notes are strongly filtered or redirected through the wall break window. CLI controls:

```powershell
python scripts/python/audio_analyzer.py --audio "assets/audio/audio.wav" --walls --wall-duration-beats 8 --wall-min-gap-bars 8 --wall-rate-bars 12 --wall-anticipation 1.85 --wall-density-multiplier 2.6 --wall-preparation-window 0.9 --wall-recovery-window 0.85 --wall-rest-window 1.0
python scripts/python/audio_analyzer.py --audio "assets/audio/audio.wav" --no-walls
python scripts/python/audio_analyzer.py --audio "assets/audio/audio.wav" --wall-override wall_events_override.json
```

`--wall-override` accepts either a JSON array of wall events or a beatmap-like object with an `events` array, so generated timing can be manually adjusted after analysis without changing renderer visuals.

Long/hold notes are generated by a separate deterministic pass over sustained RMS/low-onset windows after ordinary lane assignment and wall selection. A hold event has `type: "hold"`, `lane`, `time`/`start`, `duration`, `end_time`/`end`, and `side`/`foot`; holds do not replace ordinary notes in COMBO/SRT output. The generator rejects holds that would overlap ordinary notes on the same foot/side, violate same-lane min gap, or cross blocked lanes during the expanded wall-volume clearance window. While a left hold is active, ordinary notes must be on right lanes `2-3`; while a right hold is active, ordinary notes must be on left lanes `0-1`. CLI controls:

```powershell
python scripts/python/audio_analyzer.py --audio "assets/audio/audio.wav" --holds --hold-rate-bars 8 --hold-min-duration 1.0 --hold-max-duration 2.4 --hold-min-gap 1.35
python scripts/python/audio_analyzer.py --audio "assets/audio/audio.wav" --no-holds
```



## Neon Half-Lane Walls

Renderer visuals are configured separately in `assets/models/wall_visual_config.json` so changing wall height, glow, opacity, or safe-lane color does not change deterministic analyzer timing. Current defaults were calibrated from local `assets/images/background/reference_fullhd.mp4` frames extracted with the bundled FFmpeg:

- `25.000s`: right-side wall / cyan-magenta full-height reference.
- `75.000s`: left-side wall / high cyan span reference.
- `86.000s`: left-side wall / magenta-blue glow reference.
- `96.000s`: right-side wall / blue-violet glow reference.

Measured masks from those frames gave cyan around RGB `(50,255,255)` and magenta/violet around RGB `(115-128,0,226-231)`. Each wall is now a cached modular scene assembled from the existing sci-fi GLB-derived panel asset, with a restrained dotted neon face instead of runtime-built complex geometry. A six-instance `DodgeObstaclePool` is prewarmed with shared per-instance materials; no model load, instantiate, material duplication or destroy happens while a wall is travelling. `wall_length_z` defaults to `24.0` with a safe range of `8.0..36.0`.

During the default `1.85s` anticipation and until a wall passes, the two free lanes are highlighted with a soft, non-pulsing cyan flow guide. The legacy config key `safe_lane_pulse` controls only its flow speed; brightness stays stable. For `wall_left`, safe lanes are `2-3`; for `wall_right`, safe lanes are `0-1`. Camera dodge is renderer-only and frame-locked: `wall_right` shifts the camera left, `wall_left` shifts it right, then returns to the configured base `camera_x` with no accumulated drift. The obstacle itself never fades at its choreography end time: it remains readable and is recycled only when the entire trailing edge is behind the camera. Defaults are `camera_dodge_distance=1.05`, `camera_dodge_in_duration=0.55`, `camera_dodge_hold=0.25`, `camera_dodge_return_duration=0.70`, and `camera_dodge_easing=sine`, with safe ranges stored in `assets/models/wall_visual_config.json`.

Preview smoke:

```powershell
godot --rendering-driver opengl3 --path . --fixed-fps 10 -- --wall-preview --wall-preview-heights=3.2,4.8,5.8 --no-background-video --render-clock=frame --clock-fps=10 --clock-stop-after=10.5 --frame-sequence-dir=output/diagnostics/wall_preview_frames
```

The preview shows alternating pooled `wall_left` and `wall_right` modular volumes, soft safe-lane flow, camera dodge in both directions, complete pass-by/recycle behaviour, next-cell receptor rings, plus left- and right-side hold strips with front footprint caps. Pool integrity is checked independently with `godot --headless --path . --script res://scripts/godot/obstacles/dodge_obstacle_pool_smoke_test.gd`.

## Hit Timing

The lower target cell is the authoritative receptor/hit plane. Tap notes and hold starts trigger through a single `hit_trigger` event when the latency-compensated live song time, or the frame-locked movie time, reaches the event hit time. The trigger is one-shot per note/hold start for receptor flash and hit VFX only: there are no gameplay SFX, no foot-thump layer, and no hold-end sound.

`assets/models/wall_visual_config.json` exposes `global_audio_offset_ms` and `visual_hit_offset_ms`; the analyzer GUI exposes the same controls in the Guidance & Preview section. Godot timing follows the official rhythm-game pattern: `AudioStreamPlayer.get_playback_position() + AudioServer.get_time_since_last_mix() - AudioServer.get_output_latency()`, then applies `global_audio_offset_ms`. The default `global_audio_offset_ms=28.0` is the midpoint between the previous late-feeling `+56ms` and early-feeling `0ms`. In a graphical run, press `[` to make steps earlier by 5ms and `]` to make them later by 5ms; hold Shift for 1ms nudges. Frame-locked Movie Maker renders stay on exact frame time unless an explicit visual hit offset is provided.

Timing calibration can be reproduced from a screen recording or generated AVI:

```powershell
python scripts/python/timing_diagnostics.py --video "path\to\recording.mp4" --beatmap output\neon_track.json --source-audio "assets\audio\audio.wav" --prefix user_recording_calibrated
```

The renderer also accepts CLI overrides for calibration runs: `--global-audio-offset-ms=28` and `--visual-hit-offset-ms=0`. The diagnostic CSV includes `expected_beat`, `receptor_cross_frame`, and `error_ms`; summary JSON reports median/p95 and start/middle/end drift checks.

## Render

Import once in Godot, then render:

```powershell
godot --path . --editor --quit-after 2
godot --rendering-driver vulkan --path . --resolution 2560x1440 --write-movie output/renders/output.avi --fixed-fps 60 -- "--audio=assets/audio/audio.wav" "--render-clock=frame" "--clock-fps=60"
```

F10 now triggers the same one-click final MP4 job as the `Снять MP4` button. It copies the current live tuning values, renders from 0:00 to the exact audio duration, encodes the final H.264/AAC file and opens `output/renders/` when complete.

For live composition tuning, double-click `run_visual_tuning.bat`. The normal MP4 preview opens together with the `Track tuning` panel. Use `Whole track height` to move the complete gameplay road vertically and `Save default` to reuse the current values on the next launch. In `One-click MP4 Export`, choose the resolution/FPS and press `Снять MP4`: the job starts at 0:00, stops at the exact audio duration, encodes H.264 on NVIDIA when available (CPU fallback otherwise), removes its temporary AVI and opens the completed MP4 in `output/renders/`.

For the fastest capture, press `● СНЯТЬ ВИДЕО — ВСЁ АВТОМАТИЧЕСКИ`. Godot opens OBS when needed and prepares a dedicated composition: the original MP4 is a silent looping lower Media Source, the complete source WAV is a separate non-monitored Media Source, and the transparent Godot window is the upper Window Capture source. This lets a short background clip cover a longer song without cutting its audio. It keeps Godot in a regular window so Windows Graphics Capture continues while other applications cover it, shows a 3-2-1 countdown, starts OBS recording and restarts all sources at 0:00. The desktop is never captured; desktop and microphone inputs are temporarily muted and later restored, while Godot is also muted locally, so the computer remains free for games, work and unrelated music. Do not manually minimize or close the Godot renderer while it is recording; simply switch to another app with Alt+Tab. A monotonic recording watchdog uses the actual WAV duration and stops OBS even after Godot's audio player resets its position at EOF. It then restores the previous scene and audio-input mute states, opens the finished MP4 and closes the renderer. The helper connects to OBS WebSocket through `127.0.0.1`, with password authentication kept enabled.

Or run:

```powershell
.\render_video.ps1 -Audio "assets/audio/audio.wav" -FixedFps 60 -Resolution 2560x1440 -Godot "C:\path\to\Godot_v4.7.1-stable_win64.exe"
```

## MP4 Background

Place one background video at `assets/images/background/background.mp4` and run the project normally with F5/F6. The newest MP4 in that folder is selected automatically. Do not pass `--no-background-video`; headless runs intentionally use the procedural fallback.

Normal graphical preview uses the bundled `ffplay.exe` as a continuous borderless native player behind a per-pixel-transparent Godot window. Godot draws only the road, cues, obstacles, VFX and HUD above it. There is no raw-frame pipe, no frame queue, no `_process()`-driven MP4 frame selection, no Y/UV texture upload and no temporary frame directory. The original MP4 is never modified, plays at `1.000x`, keeps its own timestamps and loops inside the native player. Successful startup prints `backend=external_ffplay_window` and `manual_frame_upload=false`.

Preview and Movie Writer intentionally use different backends. Preview is ordinary realtime playback independent of Godot FPS. Movie Writer/F10 cannot capture another native window, so it retains the internal deterministic FFmpeg sampler keyed by `output_frame_index / output_fps`. Source 25/30/60 FPS is not converted to a fixed preview FPS; a 25 FPS source remains 25 FPS and preserves its original duration.

On Windows the project uses Direct3D 12 for correct per-pixel composition. Vulkan was rejected by a static color-reference test because its transparent swapchain visibly raised black levels; D3D12 reproduced the native-player control region (`YAVG 20.737` vs `20.602`) without any ffplay video-filter chain or brightness, contrast and saturation correction. FFprobe logs codec, dimensions, FPS, duration, pixel format, color range/space, bitrate, profile, level and VFR status. Pass `--debug-video` for source FPS, player position/duration, `1.000x` speed, render FPS and player state. For screen recording, capture the display/desktop composition; a recorder configured to capture only the Godot window may omit the separate background window.

`--background-video=path/to/file.mp4` selects an explicit MP4 for a run. `--internal-background-video` forces the older in-Godot sampler for diagnostics; it is not the recommended recording path.

Verified local dependency details are recorded in `third_party/ffmpeg/README.md`. The binary used here is BtbN `ffmpeg-master-latest-win64-lgpl.zip`, build `N-125773-g7002e01c19-20260726`, SHA-256 `593056977e17f97773dd81f538accdc3e720cb767a2e5014819238393790aa13`, LGPL FFmpeg build; BtbN build scripts are MIT licensed.

Timing acceptance helpers:

```powershell
godot --path . --script res://scripts/godot/_test_external_background_realtime_speed.gd -- --video=res://output/diagnostics/background_video_tests/h264_1080p_25fps_4s.mp4
godot --path . --script res://scripts/godot/_test_external_background_loop.gd -- --render-clock=audio --no-tuning-gui
godot --path . --script res://scripts/godot/_test_background_offline_sampling.gd -- --video=res://output/diagnostics/background_video_tests/h264_1080p_25fps_4s.mp4 --test-output-fps=60 --test-duration=2
```

The audit, root cause and current 25/30/60 FPS evidence are in `docs/BACKGROUND_VIDEO_TIMING_AUDIT_2026-08-11.md`.

## Lane Validation

Use the standalone checker to verify the production beatmap, beat-grid metadata, deterministic lane assignment, wall event constraints, hold event constraints, safe-lane mirroring, renderer visual config ranges, min-interval and anti-burst constraints, reference assets, headless clock smoke, and wall/hold movie smoke:

```powershell
python scripts/python/validate_lanes.py --godot "C:\Users\BAZA\Documents\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64_console.exe"
```

It replays the embedded beatmap and beat grid in `output/neon_track.json`, validates wall and hold event subsets against generation diagnostics, regenerates analyzer output twice from `assets/audio/audio.wav`, checks the optional background video, verifies wall/camera/timing visual config ranges, runs a short frame-locked headless smoke twice, and writes `output/renders/wall_preview_smoke.avi` for wall/hold preview smoke. The movie smoke is probed with FFprobe and must report real duration and frame count, and its `hit_trigger` diagnostics must stay within one 60fps frame for taps and hold starts.

## Deterministic Render Clock

Movie Maker and headless validation use a frame-locked render clock instead of audio playback latency. In that mode, note spawning, note motion, and hit diagnostics all read the same fixed frame time, so repeated runs at the same fps produce the same `CLOCK_DIAG` file.

To verify it without touching production timing files:

```powershell
godot --path . --headless --quit-after 2 -- "--render-clock=frame" "--clock-fps=60" "--clock-diagnostic=6" "--clock-diagnostic-file=res://_clock_diag.log" "--clock-stop-after=6"
```

## BPM / Beat Grid Check

To run the analyzer without overwriting production timing files, write to temp outputs:

```powershell
python scripts/python/audio_analyzer.py --audio "assets/audio/audio.wav" --track _tmp_neon_track.json --subtitles _tmp_combo.srt
```

Repeat the same command to verify deterministic output; generated `notes` and `events` JSON should be byte-identical for the same local audio file, CLI parameters, override file, and dependency versions.

## Acceptance Criteria

- Analyzer emits deterministic `wall_left` / `wall_right` events for any audio track unless `--no-walls` is used.
- Analyzer emits deterministic `hold` events unless `--no-holds` is used; holds respect rate/min-max duration/min-gap settings and never conflict with ordinary notes on the same foot/side during the hold window.
- Wall events alternate sides, respect duration/min-gap settings, include mirrored `safe_lanes`, and never overlap.
- Active wall windows contain no ordinary notes on blocked lanes, and holds are kept out of blocked wall volumes with clearance so long strips do not pass through the parallelepiped.
- Godot renders each wall as a volumetric neon block and each hold as a cyan/magenta lane strip with a front footprint cap, all moving on the frame-locked clock; background MP4 is supported with procedural fallback.
- Safe-lane highlight appears on the two unblocked lanes from anticipation through wall passage, and camera dodge mirrors correctly for `wall_left` and `wall_right`.
- Tap and hold-start hit triggers fire receptor flash and VFX from one authoritative timing path, with movie-smoke diagnostics no more than one 60fps frame late; gameplay SFX are removed entirely.
- COMBO subtitles and silhouette assets are untouched.
- `python scripts/python/validate_lanes.py --godot "C:\Users\BAZA\Documents\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64_console.exe"` passes.

### WAV reference corpus

Reference tracks can be profiled together without copying or modifying the
source WAV files.  The report measures tempo, onset density, beat-vs-offbeat
phase, pulse clarity, dynamic range, section contrast, and each track's
relative position inside the corpus:

```powershell
python scripts/python/reference_corpus.py `
  --audio "C:\path\to\reference-a.wav" `
  --audio "C:\path\to\reference-b.wav" `
  --output output/reports/reference_corpus.json
```

The normal analyzer also writes a track-level `movement_calibration` block.
V4 uses its `phase_preference` when scoring candidate phrases, so a syncopated
track favors readable composite/boxing/rhythm-runner patterns while a clear
downbeat track keeps more grounded base/jump/lateral vocabulary.  This affects
movement choice, not just raw note density.
