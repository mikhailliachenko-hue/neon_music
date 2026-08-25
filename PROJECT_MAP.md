# Project Map: Neon Footstep Renderer

Last updated: 2026-08-25

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
- `lane_assignment.py` - deterministic lane assignment, difficulty settings, anti-burst rules, the persisted one-or-two simultaneous-foot safety cap, wall constraints and reference-hand-hold settings.
- `phrase_grid.py` - phrase grid V2 contract, movement metadata attachment, phrase/block/section annotation.
- `music_expression.py` - music-aware features: optional neural meter, sections, accents, novelty, musical events and track-level `movement_calibration` (`phase_preference`, offbeat/contrast/density/impact/variation/recovery axes).
- `phrase_readability.py` - compact authored 32-beat templates and structural diagnostics. Enforces `Teach -> Repeat -> Mirror -> Payoff`, one action family per 8-count, at most five movements/two broad families per phrase, plus stable 64-beat mechanic chapters.
- `choreography_v3.py` - deterministic semantic movement library and phrase movement plan.
- `choreography_v4.py` - canonical Beat Grid V2/Beatmap V4 generation, music-scored readable candidates, two-phrase mechanic chapters, micro-rises, motif memory, safe compound grammar, body counterpoint, rare `DOUBLE_HAND_HOLD` accent projection, long-step payoffs, sparse jump/duck challenges, final callback, obstacle projection and V4 validation/audit. Current rules contract: `choreography_rules.v4.5`.
- `choreography_concurrency.py` - deterministic final renderer-note safety pass. It counts the actual expanded foot targets (including multi-lane notes), preserves complete left/right pairs and guarantees the Analyzer GUI cap of at most two simultaneous foot targets.
- `choreography_ornaments.py` - deterministic music-ranked 8-count detail pass. It adds at most two safe internal hits to ordinary hand/foot blocks, targets 2/3/4 hit moments by section density, forbids runs longer than two adjacent beats, and leaves jump/duck/walls/holds/long rails untouched. It also emits optional hand-position and mirrored foot-rail trajectory metadata; older JSON remains valid.
- `generate_choreography_v4.py` - deterministic V4 wrapper; reads/writes `output/neon_track.json`, synchronizes the regenerated movement projection into embedded `beat_grid`, regenerates embedded and standalone `combo.srt`, and supports `--vertical-slice` for the legacy 96-beat regression.
- `reference_corpus.py` - read-only multi-WAV profiler. Compares tempo, onset density, pulse/offbeat phase, dynamics, section contrast and relative positions without copying source WAVs.
- `validate_lanes.py` - broad acceptance gate. Resolves audio from the active track, routes V1/V3 through legacy replay and V2/V4 through `validate_v4`, checks deterministic full regeneration and Godot frame/movie smokes. Missing optional reference MP4 no longer blocks procedural smoke.
- `timing_diagnostics.py` - aligns video recording/render with source audio and measures visual hit timing.
- `validate_choreography_v3.py` - V3 choreography hard/warning validator.
- `apply_phrase_grid.py`, `generate_vertical_slice_v3.py`, `validate_lanes.py` - utility CLIs.

### `scripts/godot/`

Runtime renderer scripts.

- `main.gd` - heart of renderer. Loads inputs, manages clock/audio timing, spawns notes/walls/holds, background video, debug overlays, hit timing diagnostics and execution deck. Before music starts, one real opening step and the shared step-impact shader are rendered under the existing loading cover. Footprint frames use thin volumetric bars and one cached StandardMaterial per side instead of compiling a separate spatial shader material for every note. Together these changes move the common first-use work ahead of the small Windows audio buffer without precompiling every rare VFX family. Decorative white stage-to-stage/combo connector ribbons are no longer built or updated. March/run/reset ground cues are normalized to ordinary left/right shoe-print steps. `SMALL_JUMP`/`JUMP` are also projected as two synchronized familiar step platforms on each landing, not as a separate beam symbol. Simultaneous two-foot hits add a centered camera stomp and stay alive after judgment until their full rail tails pass the player; trajectory metadata no longer introduces a hard-coded leftward camera pull. Duck adds one centered visual, one camera dip and one short impact reaction. Movie Writer uses a deterministic StandardMaterial impact flash, expanding torus and 16 volumetric shards; the richer shader/particle family remains for interactive runs.
- `note.gd` - `RhythmNote`; visual form for foot pads and hand targets, lane position, semantic cue shape and shatter. Ordinary steps use one grounded volumetric Quaternius sci-fi puck, contact bed and one mipmapped shoe decal/frame; the removed legacy panel, circular halo and duplicate rims can no longer merge into a second silhouette. X/Z approach motion stays locked to the road instead of vertically pulsing like an overlay. Hand hits use a faceted shared impact token with distinct left/right fist artwork. Long double-foot rails are spawned at full cached length, always have approach/judgment footprint caps, and can follow optional smooth mirrored `straight`/`outward`/`inward` trajectories while old JSON stays straight. `DOUBLE_HAND_HOLD` is an explicit hit-travel-hit phrase: a 108%-target-width translucent volume connects the first pair of gloves to a second scored pair, stays on the approach side of the judgment plane and shortens as the terminal gloves arrive. Duck uses one cohesive dark glass-and-neon squashed container instead of duplicated fence geometry.
- `gameplay_cue_kit.gd` and `assets/models/gameplay_cues/` - cached shared model/material family for STEP and PUNCH cues. It wraps existing imported CC0 GLTF resources instead of generating gameplay geometry or loading models per note; cyan/left and magenta/right remain the stable semantic contract.
- `foot_rail_trajectory.gd` - validates the optional rail contract and evaluates allocation-free mirrored lane interpolation with a legacy straight fallback.
- `receptor.gd` - `NoteReceptor`; hit plane flash.
- `hit_effect.gd` - `HalftoneDiamond`; hit VFX families for steps/jumps/directional/combo. Single punches animate six-frame ready-made Cethiel CC0 blue/purple arcs; finale callback hits add a track-wide ready-made Kenney CC0 light-mask ring without increasing gameplay difficulty.
- `hit_particle.gd` - GPU particle burst for hits.
- `_capture_gameplay_visual_review.gd` - deterministic three-frame visual acceptance (`before` / `impact` / `settled`) for unified low step platforms, full-length double-foot rails, hand-target volumes and hit fragmentation. Full hit-travel-hit timing is additionally checked through the real fixed-clock main scene.
- `background_external_player.gd` - canonical graphical-preview MP4 path. It launches bundled `ffplay.exe` as a continuous borderless native player behind the transparent Godot game window. MP4 timing is independent of Godot `_process()`/render FPS; there is no raw-frame pipe, frame queue, texture upload or disk-frame cache. FFprobe records native codec/FPS/duration/color/VFR diagnostics. Windows uses D3D12 because a static reference proved Vulkan transparency washed out the native video; no creative video color filter is applied.
- `run_obs_overlay.bat` starts the dedicated recording mode (`--obs-overlay`): Godot exposes only a transparent game layer and does not launch/decode the MP4. OBS owns `assets/images/background/background.mp4` as the lower Media Source and captures the Godot window with transparency as the upper Game Capture source, producing one recording canvas.
  The launcher uses `scripts/run_obs_overlay.ps1` to apply per-pixel alpha through
  a temporary ignored `override.cfg` only for that process and restores any prior
  override after the window closes.
- Ordinary F6/project launches explicitly reset viewport and native-window
  transparency before background selection. This prevents an earlier OBS or
  external-player session from leaking desktop/Chrome through the tunnel;
  only the explicit `--obs-overlay` path may keep an alpha window.
  Ordinary F6 resolves tunnel ownership after the generator is initialized and
  reasserts an opaque native window after pipeline warmup. This prevents the
  legacy external-MP4 overlay from leaking transparent compositing into level
  preview or normal gameplay. Project-level per-pixel alpha is disabled by
  default; only the explicit OBS overlay path opts its own process back in.
- `run_visual_tuning.bat` starts a desktop-safe 1280x720 graphical preview with the background MP4 and the live `Track tuning` panel; the selected final export resolution remains independent. The native video and transparent Godot layer are aligned visually, but the Godot window is no longer forced above every Windows app. `Whole track height` moves the road, receptors, notes and lane lines together; the individual height sliders provide fine offsets. `Save default` writes the current camera/track/visual values to `assets/models/wall_visual_config.json` for future launches. The large fixed `● СНЯТЬ ВИДЕО — ВСЁ АВТОМАТИЧЕСКИ` button delegates to `scripts/obs_auto_record.ps1`: through an authenticated OBS WebSocket connection to `127.0.0.1` it builds a dedicated composition from a silent looping original MP4, the complete source WAV and transparent Godot Window Capture. Separating the WAV prevents a shorter background clip from cutting a longer song. Auto-recording deliberately keeps Godot windowed so Windows Graphics Capture survives Alt+Tab and occlusion; the renderer must not be manually minimized or closed. It never captures the desktop, temporarily mutes desktop/microphone sources and restores their prior states, records the WAV directly without local monitoring and mutes Godot locally. A monotonic watchdog stops OBS by the actual WAV duration even after AudioStreamPlayer resets at EOF; then the previous OBS scene is restored and the finished MP4 opens. The user can use other applications, play games and listen to unrelated audio during the recording. `Снять MP4` inside the scroll remains the slower offline option using `scripts/render_mp4_job.ps1` and NVIDIA H.264 with a CPU fallback.
- `background_mp4_backend.gd` - internal deterministic MP4 sampler retained for Movie Writer/F10 only, because an external native window cannot be captured by Godot's offline writer. It samples by output timestamp and keeps the existing NV12 Y/UV shader path. `_test_external_background_realtime_speed.gd` covers native 25/30/60 duration, `_test_external_background_loop.gd` crosses the real 120-second loop boundary, `_capture_external_background_composite.gd` verifies the final layered screen, and `_test_background_offline_sampling.gd` covers offline timestamps.
- `vfx_preview.gd` and `_capture_vfx_preview_frame.gd` - preview/smoke scene tooling.
- `_accept_*_check.gd` - acceptance helper scripts.
- `tunnel/neon_tunnel_generator.gd` - Forward+ infinite Neon Tunnel streamer.
  It reuses 8 pooled `TunnelSegment` scenes, consumes the existing beat/phrase/
  8-count/32-count adapter and changes only the decorative world root.
  Production frame worlds keep `continuous_frame_rhythm` enabled, so every
  recycled cell receives authored architecture instead of occasionally falling
  back to an empty floor-only layout. PackedScenes, fitted wrappers and shared
  materials are warmed before playback; streaming only reconfigures and moves
  the fixed pool.
  The optional wall spectrum remains available but is disabled in production.
  Music beat/drop never moves the tunnel camera;
  `tunnel_camera_motion_controller.gd` responds only to gameplay actions.
  CYBER AWAKENING uses the minimal `RhythmFrames` world: repeated authored
  Quaternius frames, a dark Kenney road and sparse particles. Gameplay actions
  launch a color wave that travels through the cached frames along tunnel depth;
  frames no longer scale or flash together. No wall or ceiling can enter the
  dance corridor.
- `tunnel/tunnel_level_preset.gd` and `resources/tunnel/dance_levels/` - the
  data-driven library of 27 Dance Mode levels. Their production mapping resolves
  to six curated world families: Pinterest Prism, Rhythm Frames, Rhythm Circle
  Frames, Rhythm Square Frames, Rhythm Tall Frames and Rhythm Star Frames.
  Pinterest Prism is the primary reference-directed family: a regular octagonal
  wrapper built from ready-made Quaternius rail modules, fitted around rather
  than on top of the gameplay road. The existing Track tuning GUI
  selects/reseeds/previews these Resources at runtime; all of them share the
  generator, segment scenes, resource cache and fixed eight-segment pool. Each
  preset also calibrates steady GLB-frame readability independently from bloom
  and action-wave strength, so thin dark silhouettes and broad gates share a
  consistent exposure without one global brightness multiplier.
- `tunnel/tunnel_world_style.gd`, `tunnel/tunnel_world_asset_set.gd` and
  `resources/tunnel/worlds/` - data-only spatial profiles and explicit modular
  GLB sets. The six production families use thin fitted frame silhouettes, a
  clean modular GLB floor and a dark glossy shell. Procedural guide rails,
  floor-line effects and wallpaper/background planes are disabled in these
  worlds; opaque colour, fog and sparse reflections come from the environment.
  The former production light-grid, gate, industrial, solar and quantum mappings
  remain archived resources but are no longer selected by the production library.

#### Pinterest Prism Gold Master

- `VIOLET GRID RUNNER` is the reference Gold Master. It resolves to the dedicated
  `pinterest_prism_gold_master` style and asset set; it does not modify the other
  production worlds. Its pooled `Shell` slot composes the existing
  `WallBand_Straight`, `TopSimple_Straight`, `template-floor-big` and
  `Prop_Light_Wide/Corner` GLB/GLTF modules outside a verified `4.4 m` gameplay
  half-clearance. Three cached portal wrappers provide prism, circle and clean
  energy silhouettes without procedural complex geometry.
- A complete preset `color_palette` is authoritative for the environment:
  index `0` is primary, `1` is accent and `2` is background. Shadow, crest and
  floor tones are derived once by the shared material controller; an incomplete
  legacy palette falls back per colour to `TunnelTheme`. Gold Master uses Prism
  Orchid (`#6A2D91`, `#C33DBB`, `#05030C`) with the action-wave gradient
  `#52E9FF -> #A454FF -> #FF56CF`.
- Gold Master is the first production world using the opt-in environment-sky
  background contract. `TunnelLevelPreset.background_texture` is wrapped once
  in a cached `PanoramaSkyMaterial` when `lighting_settings.sky_background_enabled`
  is true; `sky_background_energy` controls calm exposure and
  `sky_background_stage_mix` allows only a restrained smooth 32-count lift.
  `sky_background_yaw_degrees` rotates authored peripheral detail away from the
  clean gameplay axis without changing the camera or segment transforms.
  A sky-enabled preset also sets `fog_settings.sky_affect` independently from
  corridor fog density: fog still provides depth on GLB modules, but it no
  longer collapses an infinitely distant panorama into the background colour.
  The texture is never reloaded on beat/action/recycle, and the old far-plane
  background remains available to legacy worlds. Transparent OBS/external-video
  mode always wins and restores `BG_CLEAR_COLOR`, so the sky cannot cover the
  separately composited MP4.
- `assets/tunnel/backgrounds/prism_orchid_panorama_v1.png` is Gold Master's
  production 2:1 equirectangular panorama. It keeps the forward gameplay axis
  dark and moves soft orchid/cyan nebula depth into the peripheral openings of
  the modular shell. `preview_texture` deliberately remains the separate 16:9
  selector image; preview art and runtime panorama are no longer required to be
  the same file for opt-in sky levels.
- `tunnel_visual_stage_controller.gd` expresses each 32-count as four smooth
  stages: calm, reflected build, second-colour reveal and payoff. A stage may
  blend palette, fog, architectural emission and a camera FOV push of at most
  `0.9 degrees`; it never launches a wave and never changes segment geometry
  before normal pool recycling.
- Production waves are action-only. `STEP`, `PUNCH/HAND`, `JUMP`, `DUCK` and
  `HOLD` enter through the existing action API and trigger one travelling wave;
  beat/downbeat alone changes neither wave, glow nor camera. The standalone
  preview uses a deterministic sequence of those same action calls instead of a
  beat shortcut.
- Gold Master acceptance is covered by
  `pinterest_prism_gold_master_smoke_test.gd`, palette, interaction, world-style
  and gameplay-clearance smokes. Runtime evidence belongs under
  `output/diagnostics/gold_master_prism/`; these generated captures and movies
  are not source assets and are not committed.
- `gold_master_look_variants.gd` provides three non-selector QA looks for the
  standalone preview: `dark_luxury`, `pinterest_glow` and `clean_rhythm`.
  `Pinterest Glow` is the production winner for `VIOLET GRID RUNNER`; the other
  two duplicate presentation Resources while sharing the same warmed asset set.
  Pass `--look=<name>` only when making controlled comparison captures.

#### Glass Block Chamber

- `GLASS BLOCK CHAMBER` is the second reference-grade visual slice and preset 28.
  It uses the existing generator, selector, eight-segment pool and action API;
  there is no level-specific runtime branch.
- Its authoritative `glass_block_chamber` asset set composes imported Quaternius
  `WallAstra_Straight_Flat_Window`, `Platform_Window_Wide` and `Prop_Light_Wide`
  modules with the cached Kenney road and Gold Master prism/circle portals. The
  shell remains outside a verified `4.4 m` gameplay half-clearance and leaves the
  roof open so the panorama and hero portals provide depth instead of a heavy
  ceiling slab.
- Calm presentation is graphite/aubergine metal with transparent glass inserts,
  restrained turquoise Fresnel edges and no extra dynamic lights. Imported GLTF
  glass keeps its authored alpha instead of being flattened to an opaque surface.
  The chamber now carries an explicit calm readability calibration: stronger
  ambient/key midtones, a restrained shader body fill and a small per-level
  exposure lift reveal the PBR panels without increasing bloom or reducing the
  brightness hierarchy of cyan/magenta gameplay cues. All RhythmFrames worlds
  share a low steady floor/frame fill, so dark presets remain readable between
  action waves without adding runtime lights.
  Architecture deliberately avoids gameplay cyan: left/right cues retain pure
  cyan/magenta and remain the brightest objects over a dark road backdrop.
  Seven frames fill each 18 m segment; prism and circle groups are both warmed
  once and selected from the cache, producing dense variation without runtime
  PackedScene loads or objects entering the gameplay corridor.
  Beat and downbeat do not illuminate the shell. A gameplay action launches one
  distant `cyan -> violet -> rose` travelling wave; 32-count staging changes only
  palette balance, fog and a sub-degree FOV envelope.
- Runtime panorama is reused from the cached Prism Orchid sky. No texture, scene,
  material, light or particle is instantiated in response to music or actions.
- L1 coverage is included in `dance_level_smoke_test.gd`,
  `tunnel_world_style_smoke_test.gd` and `tunnel_gameplay_clearance_smoke_test.gd`.
  Forward+ `calm`, `action` and `finale` evidence lives under
  `output/diagnostics/glass_block_chamber/` and is not committed.

#### Ideal Dance Mode level formula

This contract is the acceptance gate for every production world, independent of
which GLB wrapper or theme it uses:

- Gameplay owns the centre. The road, notes, receptors and action envelope never
  inherit decorative transforms. A centred frame declares an inner half-width of
  at least `4.4 m`, an opening bottom at or below `-2.05 m` and an opening top at
  or above `4.3 m`. Closed rings additionally put their outer bottom at or below
  `-3.0 m`, so the lower arc wraps underneath the road instead of sitting on it.
- The asset set owns frame fit for every spatial profile. `frame_target_*` is
  authoritative for `RhythmFrames`, `OpenHighway` and future profiles; profile
  hard-codes may provide defaults but must never override a verified GLB fit.
- Depth rhythm is regular rather than random: an `18 m` segment carries `6-8`
  thin frames at a `2.25-3.0 m` cadence. The spacing continues across pooled
  segment boundaries, creating a dense readable corridor without gaps or a
  visible recycle seam.
- Visual hierarchy follows an approximate `70 / 25 / 5` split: 70% dark neutral
  glossy shell/floor, 25% readable low-emission architecture and at most 5%
  bright accent/action wave. The floor stays clean and no wallpaper plane is
  pasted behind the modular world. Use no more than two saturated hues plus
  neutral; cyan and
  magenta gameplay cues remain the brightest local objects. Palette pairs should
  be analogous (for example wine -> magenta -> lilac or coral -> amber -> pink),
  with a near-white crest used briefly instead of filling the whole model with
  maximum saturation.
- Architecture is calm between actions. STEP/PUNCH/JUMP/DUCK launch the existing
  cached depth wave with a `35-55 ms` portal-to-portal delay, `80-140 ms` attack
  and `320-520 ms` release. Its colour travels `cyan -> violet -> pink`; only
  gameplay actions can launch it. The wave changes emission/colour only; it never
  scales frames, creates lights or drives continuous camera shake. Beat-only
  flashing stays disabled in production.
- Composition changes at phrase/section scale, not per frame. A 32-count may move
  through a controlled `2 -> 3 -> 4 -> 3` density arc or swap one silhouette and
  palette, while the gameplay corridor and pool size remain fixed.
- Runtime budget is exactly eight pooled `TunnelSegment` nodes and `48-64`
  repeated frame instances for the `6-8` frame cadence. GLB scenes, fitted
  wrappers and materials are cached and warmed before playback; there is no
  runtime instantiate/free loop, per-ring light or per-frame material creation.
  Acceptance requires calm/action/phrase captures, no road overlap, empty cell or
  recycle seam, and a stable 60 FPS after warm-up.

`resources/tunnel/presets/` is the legacy standalone-preview library. It is not
part of the canonical 27-level production selector and must not be mixed into the
production visual audit unless that legacy path is explicitly being migrated.
- `tunnel/tunnel_asset_registry.gd`, `tunnel/tunnel_asset_library.gd` - recursive
  GLB/GLTF/TSCN intake, metadata/category filtering, bounded runtime shortlist and
  lazy PackedScene cache. `tunnel/neon_material_library.gd` owns six shared neon
  theme materials. `tunnel_asset_preview.gd` is the standalone library inspector.
- `assets/tunnel/shaders/tunnel_architecture_theme.gdshader` - shared Forward+
  material path for theme-aware GLTF architecture. It neutralizes baked source
  hues while preserving texture/normal/ORM detail; an opt-in cheap Fresnel rim
  gives glass/metal worlds readable silhouettes without extra lights. Configured
  world pools and their surface pipelines are warmed before audio starts to avoid
  streaming hitches.

### `scripts/`

- `beatmap_parser.gd` - `BeatmapParser`; normalizes the `beatmap` payload embedded inside `neon_track.json` and still understands older note-array/doc shapes when explicitly provided.

### `scenes/`

- `main.tscn` - production scene.
- `note.tscn`, `receptor.tscn`, `hit_effect.tscn`, `hit_particle.tscn` - reusable runtime objects.
  Step platforms and cylindrical hand holds use asymmetric side keys in addition
  to cyan/magenta. Long holds retain explicit start/end collars, so action and
  side remain readable without relying on colour alone.
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
- `images/` - footprints, floor grid, note textures, reference screenshots, hand targets, movement icons, VFX masks, track texture. Ordinary steps and both endpoints of a long foot rail use the same circular volumetric Quaternius platform; the former rectangular footprint frames are no longer rendered, so adjacent left/right targets retain a visible gap. Hand-target shaders preserve the authored glove color/detail instead of flattening the full alpha mask into white glow; a dark silhouette underlay, mirrored outer chevron and cooler-cyan/warmer-rose shells separate left and right at distance. `images/vfx/cethiel_weapon_slash/` contains the selected blue/purple six-frame directional arcs and its CC0 attribution; Kenney particle/light-mask selections keep separate attribution files beside their PNGs.
- `models/` - shaders, wall visual config and imported GLB assets. Duck cues use a cohesive dark squashed-container silhouette with a bright front frame; the former Kenney fence fallback has been removed. Reference jump-repeat chapters keep their familiar paired landing footprints and add one wide floor-laser cue built around the imported Quaternius `Prop_Light_Floor.gltf`. `FloorLaserPool` prewarms four complete cues, attaches exactly one to the primary note in each simultaneous pair, and recycles it only after it passes the camera. Half-lane dodge walls use the pooled `models/obstacles/reference_dodge_wall.tscn` with one cohesive cached body; the repeated modular-panel comb was removed because its perspective silhouette looked like a fence. One prewarmed object supports `low_corridor` (long 0.5 m floor-side run) and `high_side_wall` (4.6-4.9 m graphite wall with bright diagonal magenta bands); `DodgeObstaclePool` prewarms six instances and recycles each one only after its trailing edge passes the camera.
- `models/wall_visual_config.json` - renderer-only wall/camera/timing visual settings. Important for wall height/glow/safe lanes/audio offsets.
- `tunnel/` - CC0 modular tunnel library: Quaternius Modular Sci-Fi MegaKit
  (190 GLTF), Quaternius Sci-Fi Essentials (37 GLTF) and Kenney Modular Space
  Kit (40 GLB), with licenses, textures, registry and metadata sidecars.
- `worlds/tunnel/` - explicitly authored world packs used by the pooled tunnel
  streamer. In addition to the earlier city/factory modules, it contains curated
  GLB subsets from Kenney Space Station, Space Kit, Retro Urban and Nature Kit.
  Only the selected modules are imported; every pack keeps its CC0 license.
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
- Wall events include start/time, duration, blocked lanes, mirrored `safe_lanes`, anticipation and optional backward-compatible `visual_variant`. The analyzer assigns `high_side_wall` only at ranked 32-count transitions with a 64-beat minimum gap; other safe windows use `low_corridor`. After V4 generation, jump/duck/long holds keep priority while ordinary short renderer targets on the blocked half are deterministically redirected to the safe half. Three existing safe hits become a deterministic four-cell `Teach -> Repeat -> Mirror -> Payoff` dodge-dance chapter: every cell still contains both feet and one hand, but their order develops without inventing beats. Accepted walls are re-alternated after safety filtering. An incomplete safe chapter is compressed to `Teach -> Payoff` or `Teach -> Mirror -> Payoff` instead of forcing an unsafe obstacle. Godot drives the pooled obstacle, safe-lane guide and profile-specific lateral camera dodge without runtime instantiation. The same pooled mesh now has a cached emissive frame and phase-offset surface pattern, so low and high profiles read as one dark-glass neon obstacle family.
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

Latest acceptance (2026-08-18): `88 passed`; a non-writing regeneration of the active 479.4-second track produces `457` renderer notes, `432` unique hit beats and `29` controlled odd-beat accents in `18` strong eight-counts with zero V4 hard errors. All 11 accepted wall windows on the active track receive deterministic two-foot-plus-hand mini-combos without adding hit times. Jump/duck/holds/long rails remain protected. Godot editor import/parsing, note visual contracts, GPU gameplay capture, tunnel interaction smoke and a headless 60 FPS main-scene runtime all pass. The existing dirty `output/neon_track.json` was deliberately not overwritten during this acceptance run.

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

- `scripts/godot/main.gd` owns the HUD layer and hit-feedback label; the reusable timeline renderer lives in `scripts/godot/ui/dance_progress_hud.gd`.
- The compact `Music Journey + Portal Line` design is drawn natively at viewport resolution: dark glass track, level-palette fill, 8-count ticks, hollow 32-count portal diamonds, elapsed/remaining time and the current musical section.
- `MusicTimelineAdapter.timeline_overview()` exposes a read-only normalized overview of phrase-grid beats and sections. The analyzer JSON, beatmap parser and gameplay-note contract are unchanged.
- The whole bar stays spatially stable. Beat reactions affect only the current-position diamond, while section changes trigger a short 0.35-second light sweep.
- Colors follow the active `TunnelLevelPreset` immediately when a level is switched; structural markers also differ by shape so musical navigation does not depend on color alone.
- Marker controls are not spawned during playback: the component uses one custom-drawn canvas plus three persistent text labels.
- Runtime font remains the stable Kenney Future Narrow asset.
- Headless contract test: `scripts/godot/ui/dance_progress_hud_smoke_test.gd`. Visual capture evidence: `output/diagnostics/progress_hud_v2/`.

## Tunnel Color Harmony

- Every `TunnelLevelPreset.color_palette` follows the same three-slot contract: `[primary, accent, background]`. `NeonMaterialController` derives shadow, crest, floor and environment colors from those slots; gameplay cyan/magenta remains independent and must stay visually brighter than architecture.
- Production palettes are grouped into seven harmonious families rather than raw RGB themes: Prism Orchid, Wine Coral, Solar Amber, Ice Cyan, Deep Indigo, Emerald Lime and Future Silver. A level may vary value and balance inside its family, but should not introduce a third saturated architectural hue.
- Calm-frame composition target: roughly 70–80% graphite/near-black body, 15–25% dominant neon and 5–10% related accent. Saturated color belongs on trims, reflections, haze and action-wave crests—not across a whole wall body.
- Red levels use a wine/charcoal base, deep crimson primary and coral/amber accent. Avoid pure `Color(1, 0, 0)` surfaces: they flatten imported geometry and make the tunnel look detached from its background.
- Green levels use emerald/teal bodies with a restrained lime crest; violet levels stay inside aubergine/orchid/pink; ice and white levels use navy/graphite shadows so their bright edges retain depth.
- Palette changes remain data-only in `resources/tunnel/dance_levels/*.tres` and shared fallbacks in `resources/tunnel/themes/*.tres`. Do not add palette-specific branches to the generator or alter gameplay transforms.
- Forward+ harmony QA captures for representative red, violet, ice, gold and green levels live in `output/diagnostics/color_harmony_qa/`.

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
- Latest acceptance evidence: 88 pytest tests passed; a non-writing canonical V4.5 regeneration reports zero hard errors and 457 renderer notes with 29 bounded odd-beat accents. All 11 active wall windows can reuse musical hits for mirrored two-step-plus-hand patterns. Visual-contract, GPU capture, tunnel-interaction, editor parsing and headless runtime smokes pass. The existing generated track remains user-owned until it is regenerated through Analyzer.
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
