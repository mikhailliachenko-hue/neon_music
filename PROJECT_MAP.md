# Project Map: Neon Footstep Renderer

Last updated: 2026-08-18

Этот файл - быстрая карта проекта для новых диалогов с Codex. Его можно давать как стартовый контекст: здесь описано, что это за проект, где лежат основные части, как идет поток данных, какие файлы трогать для типичных задач и какие команды считать опорными.

## Коротко

`neon_music` - Godot 4.7 проект для рендера неонового rhythm/dance видео по аудиотреку. Python-пайплайн анализирует музыку, строит beat grid, назначает дорожки/движения/стены/hold-события и пишет единый `output/neon_track.json`. Для CapCut экспортируются отдельные `output/combo.srt` и `output/feedback.srt`. Godot читает `neon_track.json` и рендерит 3D-сцену: 4 lane-дорожки, объёмные step-платформы, foot/hand cues, парные hand-hold призмы, hit VFX, walls, holds, background MP4 или procedural fallback.

Текущий канонический трек: `assets/audio/audio.wav` (177.52 s). Пользовательские WAV из `Downloads` используются как read-only regression/calibration corpus и не заменяют канонический трек автоматически.

## Основной Поток

1. Audio is chosen in the GUI/CLI or imported from an AI/Gemini result.
2. `scripts/python/audio_analyzer.py` separates bass/drums through Demucs, analyzes onset/tempo/music expression and directly emits Beat Grid V2 with raw detected-beat evidence. Temporary Demucs paths are normalized back to the source audio path before persistence.
3. `scripts/python/lane_assignment.py`, `phrase_grid.py`, `music_expression.py` and `choreography_v4.py` add lanes, sections, movement calibration and semantic movement events. Simultaneous gameplay is homogeneous by contract: exactly a left/right hand pair (`DOUBLE_PUNCH` or sustained `DOUBLE_HAND_HOLD`) or a left/right foot pair (`DOUBLE_FOOT_PULSE`), never a hand and foot on the same hit. Normal full-track generation uses profile `normal`; its post-selection direction pass can place the music-spaced `jump, repeat jump, breath, duck, recovery` challenge in strong sections and a final rail/hand callback inside the last complete phrase. `warmup_first` is explicit teaching mode. The 96-beat vertical slice remains a regression wrapper.
4. Outputs:
   - `output/neon_track.json` - the only working JSON track file; contains `beatmap`, `beat_grid`, `combo_srt`, source/validation metadata.
   - `output/combo.srt` - held numeric score for CapCut; each value ends at the next distinct hit.
   - `output/feedback.srt` - sparse long-lived combo tier (`GREAT`, `PERFECT`, `UNSTOPPABLE`, etc.).
5. Godot main scene `scenes/main.tscn` runs `scripts/godot/main.gd`.
6. `scripts/beatmap_parser.gd` normalizes the embedded `beatmap` from `neon_track.json` for rendering while preserving compound-note identity (`semantic_movement`, `movement_event_id`, and simultaneous groups).
7. Renderer spawns notes, receptors, hit effects, wall/hold visuals, HUD/debug overlays, and writes movie/smoke artifacts.

## Дерево Проекта

```text
.
├─ project.godot                  Godot config, main scene: scenes/main.tscn
├─ README.md                      главная инструкция по workflow/рендеру/валидации
├─ PROGRESS.md                    хронология текущих фаз и выполненных задач
├─ PROJECT_MAP.md                 эта карта проекта
├─ requirements.txt               базовые Python зависимости analyzer
├─ requirements-advanced.txt      optional neural/music-expression backend
├─ run_analyzer_gui.bat           единый запуск GUI + автоматическая CUDA-настройка
├─ run_obs_overlay.bat            прозрачный игровой слой для единой OBS-сцены (без ffplay)
├─ run_visual_tuning.bat          живой просмотр с MP4 и панелью настройки камеры/высоты дорожки
├─ ANALYZER_QUICK_GUIDE.md        короткая памятка: что менять и не трогать
├─ render_video.ps1               PowerShell wrapper для Godot Movie Maker
├─ assets/                        аудио, изображения, модели, shaders, config
├─ data/                          static mapping/config JSON
├─ docs/                          audits, implementation plans/reports
├─ output/                        generated beatmaps, previews, reports, diagnostics
├─ scenes/                        Godot scenes
├─ scripts/                       Godot + Python логика
├─ tests/                         pytest coverage для Python contracts
├─ third_party/                   bundled external tools, сейчас FFmpeg README
└─ tools/                         вспомогательные генераторы ассетов
```

## Важные Папки

### `scripts/python/`

Музыкальный анализ и генерация данных.

- `audio_analyzer.py` - главный CLI pipeline. Делает Demucs separation, onset/tempo/expression analysis, формирует Beat Grid V2, подключает normal V4 projection и пишет единый `output/neon_track.json` плюс синхронный `output/combo.srt`.
- `analyzer_gui.py` - Tkinter GUI. Главный класс `AnalyzerApp`; основные настройки разнесены по вкладкам, действия анализа/валидации находятся в фиксированной нижней панели даже на 768p/DPI-scaled экране. Большая `START ANALYSIS` запускается также по `F5`; в шапке показан живой `GPU READY` или `CPU MODE`. При рабочей CUDA GUI передаёт Demucs строгий `device=cuda`; без доступной GPU автоматически выбирает `device=cpu` и не блокирует анализ. Во вкладке Obstacles отдельно показаны reference double-hand holds (включены, шаг 2-8 фраз) и отключённые по умолчанию legacy floor holds.
- `lane_assignment.py` - deterministic lane assignment, difficulty settings, anti-burst rules, wall constraints and persisted reference-hand-hold settings.
- `phrase_grid.py` - phrase grid V2 contract, movement metadata attachment, phrase/block/section annotation.
- `music_expression.py` - music-aware features: optional neural meter, sections, accents, novelty, musical events and track-level `movement_calibration` (`phase_preference`, offbeat/contrast/density/impact/variation/recovery axes).
- `phrase_readability.py` - compact authored 32-beat templates and structural diagnostics. Enforces `Teach -> Repeat -> Mirror -> Payoff`, one action family per 8-count, at most five movements/two broad families per phrase, plus stable 64-beat mechanic chapters.
- `choreography_v3.py` - deterministic semantic movement library and phrase movement plan.
- `choreography_v4.py` - canonical Beat Grid V2/Beatmap V4 generation, music-scored readable candidates, two-phrase mechanic chapters, micro-rises, motif memory, safe compound grammar, body counterpoint, rare `DOUBLE_HAND_HOLD` accent projection, long-step payoffs, sparse jump/duck challenges, final callback, obstacle projection and V4 validation/audit. Current rules contract: `choreography_rules.v4.5`.
- `generate_choreography_v4.py` - deterministic V4 wrapper; reads/writes `output/neon_track.json`, synchronizes the regenerated movement projection into embedded `beat_grid`, regenerates embedded and standalone `combo.srt`, and supports `--vertical-slice` for the legacy 96-beat regression.
- `reference_corpus.py` - read-only multi-WAV profiler. Compares tempo, onset density, pulse/offbeat phase, dynamics, section contrast and relative positions without copying source WAVs.
- `validate_lanes.py` - broad acceptance gate. Resolves audio from the active track, routes V1/V3 through legacy replay and V2/V4 through `validate_v4`, checks deterministic full regeneration and Godot frame/movie smokes. Missing optional reference MP4 no longer blocks procedural smoke.
- `timing_diagnostics.py` - aligns video recording/render with source audio and measures visual hit timing.
- `validate_choreography_v3.py` - V3 choreography hard/warning validator.
- `apply_phrase_grid.py`, `generate_vertical_slice_v3.py`, `validate_lanes.py` - utility CLIs.

### `scripts/godot/`

Runtime renderer scripts.

- `main.gd` - heart of renderer. Loads inputs, manages clock/audio timing, spawns notes/walls/holds, background video, debug overlays, hit timing diagnostics and execution deck. Decorative white stage-to-stage/combo connector ribbons are no longer built or updated. March/run/reset ground cues are normalized to ordinary left/right shoe-print steps. `SMALL_JUMP`/`JUMP` are also projected as two synchronized familiar step platforms on each landing, not as a separate beam symbol. Simultaneous two-foot hits add a small centered camera stomp and stay alive after judgment until their full rail tails pass the player; duck adds a camera dip plus a short impact shake. Movie Writer uses a deterministic StandardMaterial impact flash, expanding torus and 16 volumetric shards; the richer shader/particle family remains for interactive runs.
- `note.gd` - `RhythmNote`; visual form for foot pads and hand targets, lane position, semantic cue shape and shatter. Ordinary steps are low dark neon tiles with compact shoe decals. Long double-foot rails are spawned at full cached length and extend from the distant target toward the camera, so they never pop in during final approach. `DOUBLE_HAND_HOLD` uses a thin translucent guide ribbon with a bright target cap, then retracts at the judgment plane. Duck keeps the ready-made elevated Kenney 3D beam.
- `receptor.gd` - `NoteReceptor`; hit plane flash.
- `hit_effect.gd` - `HalftoneDiamond`; hit VFX families for steps/jumps/directional/combo. Single punches animate six-frame ready-made Cethiel CC0 blue/purple arcs; finale callback hits add a track-wide ready-made Kenney CC0 light-mask ring without increasing gameplay difficulty.
- `hit_particle.gd` - GPU particle burst for hits.
- `_capture_gameplay_visual_review.gd` - deterministic three-frame visual acceptance (`before` / `impact` / `settled`) for ordinary low step platforms, full-length double-foot rails, safe hand-hold retraction and hit fragmentation.
- `background_external_player.gd` - canonical graphical-preview MP4 path. It launches bundled `ffplay.exe` as a continuous borderless native player behind the transparent Godot game window. MP4 timing is independent of Godot `_process()`/render FPS; there is no raw-frame pipe, frame queue, texture upload or disk-frame cache. FFprobe records native codec/FPS/duration/color/VFR diagnostics. Windows uses D3D12 because a static reference proved Vulkan transparency washed out the native video; no creative video color filter is applied.
- `run_obs_overlay.bat` starts the dedicated recording mode (`--obs-overlay`): Godot exposes only a transparent game layer and does not launch/decode the MP4. OBS owns `assets/images/background/background.mp4` as the lower Media Source and captures the Godot window with transparency as the upper Game Capture source, producing one recording canvas.
- `run_visual_tuning.bat` starts a desktop-safe 1280x720 graphical preview with the background MP4 and the live `Track tuning` panel; the selected final export resolution remains independent. The native video and transparent Godot layer are aligned visually, but the Godot window is no longer forced above every Windows app. `Whole track height` moves the road, receptors, notes and lane lines together; the individual height sliders provide fine offsets. `Save default` writes the current camera/track/visual values to `assets/models/wall_visual_config.json` for future launches. The large fixed `● СНЯТЬ ВИДЕО — ВСЁ АВТОМАТИЧЕСКИ` button delegates to `scripts/obs_auto_record.ps1`: through an authenticated OBS WebSocket connection to `127.0.0.1` it builds a dedicated composition from a silent looping original MP4, the complete source WAV and transparent Godot Window Capture. Separating the WAV prevents a shorter background clip from cutting a longer song. Auto-recording deliberately keeps Godot windowed so Windows Graphics Capture survives Alt+Tab and occlusion; the renderer must not be manually minimized or closed. It never captures the desktop, temporarily mutes desktop/microphone sources and restores their prior states, records the WAV directly without local monitoring and mutes Godot locally. A monotonic watchdog stops OBS by the actual WAV duration even after AudioStreamPlayer resets at EOF; then the previous OBS scene is restored and the finished MP4 opens. The user can use other applications, play games and listen to unrelated audio during the recording. `Снять MP4` inside the scroll remains the slower offline option using `scripts/render_mp4_job.ps1` and NVIDIA H.264 with a CPU fallback.
- `background_mp4_backend.gd` - internal deterministic MP4 sampler retained for Movie Writer/F10 only, because an external native window cannot be captured by Godot's offline writer. It samples by output timestamp and keeps the existing NV12 Y/UV shader path. `_test_external_background_realtime_speed.gd` covers native 25/30/60 duration, `_test_external_background_loop.gd` crosses the real 120-second loop boundary, `_capture_external_background_composite.gd` verifies the final layered screen, and `_test_background_offline_sampling.gd` covers offline timestamps.
- `vfx_preview.gd` and `_capture_vfx_preview_frame.gd` - preview/smoke scene tooling.
- `_accept_*_check.gd` - acceptance helper scripts.
- `tunnel/neon_tunnel_generator.gd` - Forward+ infinite Neon Tunnel streamer.
  It reuses 8 pooled `TunnelSegment` scenes, consumes the existing beat/phrase/
  8-count/32-count adapter and changes only the decorative world root.
  The optional wall spectrum remains available but is disabled in production.
  Music beat/drop never moves the tunnel camera;
  `tunnel_camera_motion_controller.gd` responds only to gameplay actions.
  CYBER AWAKENING uses the minimal `RhythmFrames` world: repeated authored
  Quaternius frames, a dark Kenney road and sparse particles. Gameplay actions
  launch a color wave that travels through the cached frames along tunnel depth;
  frames no longer scale or flash together. No wall or ceiling can enter the
  dance corridor.
- `tunnel/tunnel_level_preset.gd` and `resources/tunnel/dance_levels/` - the
  data-driven library of 14 reference-focused Dance Mode levels. The existing Track tuning GUI
  selects/reseeds/previews these Resources at runtime; all of them share the
  generator, segment scenes, resource cache and fixed eight-segment pool. Each
  preset also calibrates steady GLB-frame readability independently from bloom
  and action-wave strength, so thin dark silhouettes and broad gates share a
  consistent exposure without one global brightness multiplier.
- `tunnel/tunnel_world_style.gd`, `tunnel/tunnel_world_asset_set.gd` and
  `resources/tunnel/worlds/` - data-only spatial profiles and explicit modular
  GLB sets. The user-facing library uses six minimal rhythm-frame silhouettes
  (open A-frame, square, tall square, open gate, circle and star) plus the
  separate LIGHT GRID RUNNER panel tunnel. The latter instances the emissive
  insert from Quaternius `Prop_Light_Wide.gltf` through pooled MultiMeshes.
- `tunnel/tunnel_asset_registry.gd`, `tunnel/tunnel_asset_library.gd` - recursive
  GLB/GLTF/TSCN intake, metadata/category filtering, bounded runtime shortlist and
  lazy PackedScene cache. `tunnel/neon_material_library.gd` owns six shared neon
  theme materials. `tunnel_asset_preview.gd` is the standalone library inspector.
- `assets/tunnel/shaders/tunnel_architecture_theme.gdshader` - shared Forward+
  material path for theme-aware GLTF architecture. It neutralizes baked source
  hues while preserving texture/normal/ORM detail. Configured world pools and
  their surface pipelines are warmed before audio starts to avoid streaming hitches.

### `scripts/`

- `beatmap_parser.gd` - `BeatmapParser`; normalizes the `beatmap` payload embedded inside `neon_track.json` and still understands older note-array/doc shapes when explicitly provided.

### `scenes/`

- `main.tscn` - production scene.
- `note.tscn`, `receptor.tscn`, `hit_effect.tscn`, `hit_particle.tscn` - reusable runtime objects.
- `vfx_preview.tscn` - preview scene.
- `tunnel/neon_tunnel.tscn`, `tunnel/tunnel_segment.tscn` - production generator
  and fallback-compatible base module. `tunnel/segments/` contains CyberRing,
  EnergyGate, Synthwave, FutureClean and SpaceNeon real-asset variants.
- `tunnel/tunnel_asset_preview.tscn` - category/size/material/Glow preview tool.
- `tunnel/levels/cyber_awakening_preview.tscn` - music-free directed-level preview
  with speed/theme/seed/density/phase overrides and optional viewport capture.
- `debug/CueOrientationTest.tscn` - visual/orientation debug.

### `assets/`

- `audio/` - active source audio and Godot imports; canonical source is currently `audio.wav`.
- `images/` - footprints, floor grid, note textures, reference screenshots, hand targets, movement icons, VFX masks, track texture. `images/vfx/cethiel_weapon_slash/` contains the selected blue/purple six-frame directional arcs and its CC0 attribution; Kenney particle/light-mask selections keep separate attribution files beside their PNGs.
- `models/` - shaders, wall visual config and imported GLB assets. Active duck/jump obstacles reuse the selected CC0 Kenney Platformer Kit `fence-low-straight.glb` as a low jump rail or elevated duck beam with neon runtime materials. Half-lane dodge walls use the pooled `models/obstacles/reference_dodge_wall.tscn`, assembled from cached modular sci-fi GLB-derived panels with low-glare shader faces; `DodgeObstaclePool` prewarms six instances and recycles each one only after its trailing edge passes the camera.
- `models/wall_visual_config.json` - renderer-only wall/camera/timing visual settings. Important for wall height/glow/safe lanes/audio offsets.
- `tunnel/` - CC0 modular tunnel library: Quaternius Modular Sci-Fi MegaKit
  (190 GLTF), Quaternius Sci-Fi Essentials (37 GLTF) and Kenney Modular Space
  Kit (40 GLB), with licenses, textures, registry and metadata sidecars.
- `CODEX_CHANGE_REQUEST_V2_CURRENT_PIPELINE.md`, `CODEX_FULL_VISUAL_MASTER_PROMPT_V6(1).md` - task/spec context from previous work.

### `docs/`

Useful for understanding current intent:

- `CURRENT_PIPELINE_AUDIT.md` / `CURRENT_BEATMAP_PIPELINE_AUDIT.md` - current contracts and pipeline state.
- `MUSIC_CHOREOGRAPHY_ANALYZER_V5.md` - design for music-aware choreography.
- `CHOREOGRAPHY_V4_IMPLEMENTATION_PLAN.md`, `CHOREOGRAPHY_V4_IMPLEMENTATION_REPORT.md`, `CHOREOGRAPHY_V4_PROGRESS.md` - V4 work.
- `VISUAL_GAP_AUDIT_V4.md`, `VISUAL_GAP_AUDIT_V6.md`, `VISUAL_IMPLEMENTATION_REPORT_V4.md`, `V6_SPRINT_CONTACT_SHEETS.md` - visual QA/history.
- `PHASE_3_4_IMPLEMENTATION_REPORT.md`, `VERTICAL_SLICE_V2_AUDIT.md` - earlier vertical slice history.

### `output/`

Generated artifacts. Usually do not treat as source unless user explicitly asks.

- `neon_track.json` - current production analyzer output and only JSON track contract.
- `combo.srt` - held numeric CapCut score generated from `neon_track.json` gameplay notes.
- `feedback.srt` - separate sparse CapCut performance-status track.
- `reports/` - validation/audit JSON.
- `reports/reference_corpus.json` - latest six-track calibration/regression summary; source WAV paths are not persisted.
- `diagnostics/` - timing, determinism and smoke diagnostics.
- `previews/` - screenshots/contact sheets for visual QA.
- `renders/` may be produced by Godot Movie Maker.
- Older `beatmap.json`, `beat_grid.json`, `data/beatmap_v4.json`, and `data/beat_grid_v2.json` are deprecated compatibility artifacts and should not be used in the normal workflow.

### `tests/`

Python contract tests:

- `test_choreography_v4.py`
- `test_music_expression.py`
- `test_phase3_choreography.py`
- `test_phrase_grid_contracts.py`
- `test_warmup_choreography.py`

## Data Contracts

Primary track contract is `neon_music.track.v1` in `output/neon_track.json`. The current canonical artifact embeds `neon_music.beatmap.v4`, `neon_music.beat_grid.v2`, `combo_srt` and validation metadata. Analyzer may keep a V3-compatible outer payload while attaching a V4 projection, but a subsequent canonical V4 generation writes direct V4. Normal workflows must not recreate standalone `beatmap.json`/`beat_grid.json`.

`neon_track.json` shape:

- `schema`, `status`, `source`, `audio`, `bpm`, `beat_interval`.
- `beatmap`: runtime note/event payload Godot reads.
- `beat_grid`: BPM/grid diagnostics, sections, phrase/movement metadata.
- `combo_srt`: backward-compatible embedded numeric score SRT; standalone exports are regenerated from gameplay notes.
- `validation_report`: AI/local validation summary when available.
- `lane_layout`: `4_lanes` or `2_cells`; `2_cells` uses only lanes 0 and 3 for the large left/right pads, with strong accents/drop/downbeats emitted as simultaneous `[0, 3]` jump notes.
- Simultaneous targets at the same millisecond increase the combo together and produce one visible number, avoiding overlapping CapCut captions.

Embedded `beatmap` shape:

- `notes`: tap/jump/hold-like notes.
- `events`: `wall_left`, `wall_right`, `hold`, and movement/obstacle-like events depending on generation path.
- `movement_events`, `phrase_plan`, `candidate_debug`, `semantic_obstacle_events`, `micro_accents` and validation summary in direct V4 output.
- `choreography_v4`: optional nested V4 bridge when the document comes directly from Audio Analyzer before canonical V4 normalization.
- Notes include timing, lanes, movement, cue archetype, phrase/count metadata and optional beat-grid annotations. Sustained hand targets carry `sustained: true` and their positive `duration`; ordinary taps carry duration `0`.
- Wall events include start/time, duration, blocked lanes, mirrored `safe_lanes`, anticipation. Their visual layer does not alter gameplay lanes: it drives a pooled half-track obstacle, a soft cyan safe-lane flow guide and the existing lateral camera dodge.
- Hold events include lane, start/end/duration, side/foot and clearance constraints.

Embedded `beat_grid` shape:

- `raw_detected_beats`, `canonical_beats`, tempo/downbeat hypotheses, coverage/residual quality and controlled fallback regions.
- selected difficulty, ramp/anti-burst settings and `generation_settings.reference_hand_holds` (`enabled`, `rate_phrases`).
- SciPy peak diagnostics.
- wall/hold generation diagnostics.
- lane assignment diagnostics.
- phrase grid, sections and movement summaries in newer phases.
- `music_expression.movement_calibration` with phase, offbeat, dynamics and scaling targets.

Current V4.5 reference rule: a mechanic is held for an establish/variation pair of 32-beat phrases. Every phrase follows `Teach -> Repeat -> Mirror -> Payoff`; each 8-count is family-focused and sparse challenge chapters replace the full phrase rather than being layered on unrelated steps. A long `DOUBLE_FOOT_PULSE` remains one simultaneous left/right landing with positive visual duration. Rare sustained hand holds own a complete hand-only payoff block. Legacy ground labels are exported as ordinary left/right shoe pads, and mixed hand/foot simultaneous groups remain prohibited.

Reference visual evidence: the earlier comparison remains documented near `07:20` in [STAY ON BEAT #5](https://www.youtube.com/watch?v=Tcl6RXETEng). The 2026-08-10 recheck compares [STAY ON BEAT #8](https://www.youtube.com/watch?v=JEu84jbp2A0) and [DANCE MODE #11](https://www.youtube.com/watch?v=I5Jp1r2mlQQ); findings, implemented rules and the ten-item backlog are in `docs/COMPETITOR_REFERENCE_REVIEW_2026-08-10.md`.

Latest visual/GUI QA artifacts: `output/reference_competitors/*contact_sheet.png`, `output/reference_competitors/*motion_sheet.png`, `output/previews/analyzer_gui_hand_holds.png`, and `output/visual_checks/gameplay_visual_review_{before,impact,settled}.png`.

Latest acceptance (2026-08-18): `78 passed`; the active 479.4-second track regenerates to `242` movement events and `416` renderer notes with zero V4 hard errors. V4.5 averages `3.97` unique movements and `0.49` broad-family switches per phrase, never exceeds five movements or two switches, and contains no phrase with three or more broad families. A second canonical regeneration is byte-identical. Godot editor import/parsing, the deterministic three-frame GPU visual review, and a headless 60 FPS main-scene runtime all pass.

Godot now looks for `res://output/neon_track.json` by default, extracts its embedded `beatmap`, and then normalizes notes/events.

AI/Gemini workflow files:

- `ai_exchange/INPUT/NEON_CHOREO_PROMPT.txt` - instruction for Gemini Notebook and YouTube/stems references.
- `ai_exchange/OUTPUT/neon_track.json` - AI result before import.
- `scripts/python/import_ai_neon_track.py` - imports AI result into `output/neon_track.json` and exports `output/combo.srt`.
- `scripts/python/validate_ai_track.py` - checks AI output for full-track coverage, density, duration mismatch and SRT completeness.
- `scripts/python/export_combo_srt.py` - regenerates both `output/combo.srt` and `output/feedback.srt` from `output/neon_track.json`.

## Commands

Install dependencies:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-advanced.txt
```

Run analyzer GUI:

```powershell
.\run_analyzer_gui.bat
```

This is the only user-facing launcher. It checks CUDA first. When NVIDIA hardware is present but GPU PyTorch is missing, the first launch automatically installs the official CUDA 13.0 wheel and verifies a real CUDA matrix operation. When no NVIDIA GPU is detected, or CUDA setup fails, it opens the GUI in `CPU MODE` instead of stopping. Later GPU launches skip installation. Choose audio and use the fixed bottom `START ANALYSIS` button or `F5`. A short list of mandatory/safe/unsafe settings is in `ANALYZER_QUICK_GUIDE.md`.

Run analyzer CLI:

```powershell
python scripts/python/audio_analyzer.py --audio "assets/audio/audio.wav" --demucs-device cuda
```

Generate V4 choreography data:

```powershell
python scripts/python/generate_choreography_v4.py
```

Profile multiple WAV references without modifying them:

```powershell
python scripts/python/reference_corpus.py --audio "C:\path\to\track-a.wav" --audio "C:\path\to\track-b.wav" --output output/reports/reference_corpus.json
```

Legacy 96-beat slice:

```powershell
python scripts/python/generate_choreography_v4.py --vertical-slice
```

Run Python tests:

```powershell
python -m pytest tests
```

Validate production lane/render contract:

```powershell
python scripts/python/validate_lanes.py --godot "C:\Users\BAZA\Documents\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64_console.exe"
```

Import Godot assets once:

```powershell
godot --path . --editor --quit-after 2
```

For the normal user workflow, press `Снять MP4` in the tuning panel (or F10) to launch the one-click final MP4 job with the current live values. The raw command below remains a developer-only Movie Writer AVI smoke:

```powershell
godot --rendering-driver vulkan --path . --resolution 2560x1440 --write-movie output/renders/output.avi --fixed-fps 60 -- "--audio=assets/audio/audio.wav" "--render-clock=frame" "--clock-fps=60"
```

Render through wrapper:

```powershell
.\render_video.ps1 -Audio "assets/audio/audio.wav" -FixedFps 60 -Resolution 2560x1440 -Godot "C:\path\to\Godot_v4.7.1-stable_win64.exe"
```

Timing diagnostics from recording/render:

```powershell
python scripts/python/timing_diagnostics.py --video "path\to\recording.mp4" --beatmap output\neon_track.json --source-audio "assets\audio\audio.wav" --prefix user_recording_calibrated
```

## Progress HUD

- Song progress HUD is built in scripts/godot/main.gd by _build_dance_hud() and updated by _update_dance_hud(song_time).
- Current design is asset-based: a ready-made OpenGameArt progress bar frame (`assets/ui/opengameart_progress_bars/bar_empty_frame.png`) with a clipped blue fill (`bar_blue_fill.png`), readable elapsed/remaining labels, and a moving dancer-silhouette marker for the current song position.
- The HUD now pulses on beatmap hit-times: the bar breathes slightly wider/brighter, the fill gets a short cyan lift, and the dancer marker pops for about 0.22s. Strong movement hits and phrase accents get a stronger pulse via _hit_strength_for_time().
- Runtime HUD font currently uses the stable Kenney Future Narrow asset; Rajdhani/Poppins were downloaded for testing, but Rajdhani caused a Godot movie-maker crash in this project and Poppins is not yet wired into main.gd.
- Source sheet for the ready-made progress bar is `assets/ui/opengameart_progress_bars/bars_2.png`; source/license notes are in `assets/ui/opengameart_progress_bars/ATTRIBUTION.md`.
- The marker bitmap is `assets/ui/silhouettes/dancer_marker_glow.png`; notes for the bitmap and the legacy SVG reference are in `assets/ui/silhouettes/ATTRIBUTION.md`.
- PNG assets are loaded as imported Texture2D resources when available, with an Image.load_from_file() fallback; the bitmap marker uses the same path.
- The central road and bloom were toned down a bit so the HUD reads cleaner over the scene.
- Short render evidence: output/renders/progress_hud_beat_pulse_smoke.avi and output/renders/progress_hud_beat_pulse_frame.jpg.
## Where To Change What

- Analyzer/contract path: `scripts/python/audio_analyzer.py`, `music_expression.py`, `phrase_grid.py`, `choreography_v4.py`, then update tests. Preserve Track V1 as the one-file envelope and Beat Grid V2/Beatmap V4 as the canonical inner contracts.
- Lane behavior/difficulty/anti-burst: `scripts/python/lane_assignment.py`.
- Music-expression intelligence: `scripts/python/music_expression.py`.
- GUI controls: `scripts/python/analyzer_gui.py`.
- Beatmap compatibility in Godot: `scripts/beatmap_parser.gd`.
- Note/cue visuals: `scripts/godot/note.gd`, `assets/images/`, `assets/models/movement_icon.gdshader`.
- Hit VFX: `scripts/godot/hit_effect.gd`, `scripts/godot/hit_particle.gd`, `assets/models/hit_vfx.gdshader`, `assets/images/vfx/`.
- Main render timing/spawn/camera/walls/holds: `scripts/godot/main.gd`.
- Wall visual tuning: `assets/models/wall_visual_config.json`.
- MP4 background behavior: `scripts/godot/background_external_player.gd` for graphical preview; `scripts/godot/background_mp4_backend.gd` plus `assets/models/background_nv12.gdshader` for Movie Writer/F10; bundled tools are documented in `third_party/ffmpeg/README.md`.
- MP4 timing audit and 25/30/60 evidence: `docs/BACKGROUND_VIDEO_TIMING_AUDIT_2026-08-11.md`.
- Validation rules: `scripts/python/validate_lanes.py`, `tests/`.
- Visual QA evidence: `output/previews/`, `docs/*AUDIT*`, `docs/*REPORT*`.

## Current State Notes

- Branch at inspection: `codex/prog-fork`.
- Worktree is dirty with many modified and untracked files. Do not revert unrelated changes.
- Full Audio Analyzer now emits detected evidence into Beat Grid V2 and uses V4 profile `normal`; `warmup_first` is no longer accidentally forced by an `Active` difficulty name.
- V4.5 dynamics use 64-beat mechanic chapters made from two 32-beat establish/variation phrases. Each phrase follows `Teach -> Repeat -> Mirror -> Payoff`; controlled jump/duck challenges replace a complete phrase instead of being layered over unrelated steps.
- Reference recheck: `https://www.youtube.com/watch?v=Tcl6RXETEng` shows simultaneous foot pairs around 03:00/03:20 and a simultaneous left/right hand pair around 05:01; these are modeled as two homogeneous pair grammars rather than combined hand-and-foot hits.
- Latest acceptance evidence: 78 pytest tests passed; canonical V4.5 regeneration reports zero hard errors and remains byte-identical on a second run. The 479.4-second active track has 242 movements, 416 renderer notes, four long hand holds, ten jump cues and ten duck cues. Phrase readability is bounded to at most five unique movements, two broad families and two family switches. Godot editor parsing, headless runtime and the three-frame gameplay/VFX review pass.
- Downbeat phase remains low-confidence/ambiguous and may benefit from the optional neural backend or manual phase selection; this is separate from detected-beat coverage.
- Generated outputs and previews are important evidence, but many live under `output/` and may be regenerated.
- There are duplicated root-level Godot files (`main.gd`, `note.gd`, `*.tscn`, shaders) plus canonical copies under `scripts/godot/`, `scenes/`, and `assets/models/`. Check actual scene references before editing root-level duplicates.

## Quick Mental Model

Python decides **when/what should happen**.

Godot decides **how it looks and renders on the frame clock**.

`output/neon_track.json` is the bridge between them; `output/combo.srt` is only the CapCut subtitle export.

`validate_lanes.py` is the broad acceptance gate.

`README.md` is the operational truth for commands.

`PROGRESS.md` and `docs/` explain why the current shape exists.
