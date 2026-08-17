# Background MP4 Timing Audit — 2026-08-11

## CURRENT VIDEO PIPELINE

- Godot core does not play this H.264 MP4 through `VideoStreamPlayer`, and no MP4 GDExtension is installed.
- Graphical preview uses `scripts/godot/background_external_player.gd`. It launches the bundled `ffplay.exe` as one continuous borderless native video window behind a transparent Godot game window.
- Preview has no decoded-frame pipe, reader queue, manual frame counter, per-frame `seek()`, `_process()` frame upload, Y/UV texture update or disk-frame cache.
- `scripts/godot/background_mp4_backend.gd` remains only for Movie Writer/F10, where an external window cannot be captured. That path samples the MP4 deterministically by output timestamp.
- OBS recording uses `run_obs_overlay.bat` / `--obs-overlay`. In that mode Godot does not launch ffplay or decode the MP4; it renders a transparent gameplay-only window while OBS plays the original MP4 once as its lower Media Source and composites both sources into one canvas.
- Choreography, beatmap, gameplay events, road geometry, obstacles and camera timing were not changed.

## ROOT CAUSE

The old realtime implementation was still a custom frame decoder: FFmpeg produced raw NV12 frames, a reader thread accumulated them, GDScript selected a frame against wall-clock time and uploaded Y/UV textures. The active MP4 is exactly 120 seconds long, and the reported slowdown began near two minutes, at the first decoder loop boundary. This made the custom queue/restart path the remaining failure point even after earlier pacing fixes.

The color complaint was separate. A static reference showed that the native player itself preserved the source, but Godot's Vulkan per-pixel-transparent swapchain raised black levels during Windows composition. The same scene under D3D12 matched the untouched player control.

## NEW ARCHITECTURE

### Graphical preview / screen recording

1. FFprobe reads codec, dimensions, native FPS, duration, pixel format, color range/space, bitrate, profile, level and VFR status.
2. `ffplay.exe` opens the MP4 once, loops internally and follows the stream timestamps at `1.000x`.
3. The player window is borderless and sized to the Godot window. Godot is a per-pixel-transparent, always-on-top gameplay overlay.
4. Direct3D 12 is selected on Windows. The MP4 receives no `-vf` chain and no brightness, contrast, saturation, range or artistic color filter; ffplay reads the source's own BT.709 TV-range metadata.
5. Closing/restarting the game terminates only the child player PID. F11 resynchronizes the player window to the new game-window rectangle.

The preview video clock is entirely independent of Godot render and physics FPS. A 25 FPS source remains 25 FPS; 30 remains 30; 60 remains 60. The source duration is not rescaled.

### Movie Writer / F10

Movie Writer runs at a deterministic fixed timestep and cannot record a separate native background window. It therefore keeps the internal sampler:

```text
video_timestamp = output_frame_index / output_fps
```

The offline renderer can run faster or slower than realtime without changing the background timeline. This path remains intentionally separate from preview.

On Windows F10 and `render_video.ps1` explicitly launch Movie Writer with Vulkan. Godot 4.7.1 crashed during the same Movie Writer smoke under D3D12, while Vulkan completed 31 frames at 30 FPS (1.033 seconds). The transparent preview still uses D3D12; offline output has no external transparent window and therefore does not need the D3D12 composition fix.

The user-facing `Снять MP4`/F10 job is wrapped by `scripts/render_mp4_job.ps1`. It validates the actual AVI frame count rather than trusting Godot's shutdown exit code, retries an incomplete render once, then muxes the original source audio and encodes H.264 through NVENC with a CPU fallback. A 1.5-second acceptance produced 45/45 video frames at 30 FPS plus 1.5 seconds of AAC audio.

### Layering and aspect

```text
native MP4 player window
        ↓
transparent Godot road / cues / obstacles / VFX / HUD
        ↓
Windows desktop composition / screen recorder
```

The player preserves aspect ratio. The project and normal capture resolution are 16:9, matching the active source. Record the display/desktop composition; a capture source restricted to the Godot HWND may omit the separate video window.

## DIAGNOSTICS

Pass `--debug-video` or `--qa-overlay` to print once per second:

- source FPS and VFR status;
- player position and source duration;
- playback speed (`1.000x`);
- Godot render FPS;
- native-player state and PID.

The active MP4 probes as H.264 High, 1920×1080, 25.000 FPS CFR, 120.000 seconds, `yuv420p`, TV range, BT.709, about 4.03 Mbit/s, level 4.0.

## ACCEPTANCE RESULTS

### Native realtime duration

Synthetic H.264 1920×1080 CFR clips were played to natural EOF. The roughly 0.32-second difference includes native window startup/teardown; playback speed reported `1.000x` in every run.

| Source | Source duration | Process elapsed | Absolute difference | Result |
|---|---:|---:|---:|---|
| 1080p25 | 4.000 s | 4.305 s | 0.305 s | PASS |
| 1080p30 | 4.000 s | 4.382 s | 0.382 s | PASS |
| 1080p60 | 4.000 s | 4.354 s | 0.354 s | PASS |
| 4K60 | 4.000 s | 4.446 s | 0.446 s | PASS |

The 4K60 case is intentionally allowed to drop late display frames (`-framedrop`) instead of stretching the timeline. Quality and smoothness still depend on codec complexity and machine capacity, but the test did not enter slow motion and preserved duration.

### Real two-minute loop boundary

The active 120-second MP4 ran continuously for 126 seconds. Before the loop the same player PID reported `116.004 / 120.000`; after the boundary it remained `PLAYING` with the same PID and reported `6.054 / 120.000`. Godot held 60 FPS through the transition. Result: PASS.

Evidence:

- `output/visual_checks/external_background_before_loop.png`
- `output/visual_checks/external_background_after_loop.png`
- `output/visual_checks/external_background_composite.png`

### Source-color preservation

A static H.264 reference was used to remove animation/timestamp differences. In a control crop outside all Godot geometry:

| Capture | YAVG | SATAVG |
|---|---:|---:|
| Native player only | 20.6016 | 3.1944 |
| D3D12 final composition | 20.7374 | 3.2132 |

Vulkan produced a visibly washed control (`YAVG` about 50.69), so it is not used for this Windows overlay. D3D12 reproduces the original player image without creative grading.

### Offline sampling

The existing deterministic acceptance remains valid: 25→30, 25→60, 30→60 and 60→60 output sampling passed with the expected frame counts and zero offline drops. A Godot Movie Writer smoke reached output timestamp 1.000 seconds with 61 sampled frames at 60 FPS while wall-clock rendering took much longer, confirming that offline render speed does not control video speed.
