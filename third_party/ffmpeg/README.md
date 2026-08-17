# FFmpeg dependency for MP4 background playback

Graphical preview uses the local `ffplay.exe` as a continuous native player for
the newest MP4 under `assets/images/background/`. It runs behind a transparent
Godot window, follows source timestamps at 1.0x and does not send decoded frames
through Godot. FFprobe supplies metadata and color-range diagnostics. Offline
Movie Writer cannot capture the external window, so it retains the separate
FFmpeg NV12 sampler keyed by output timestamps. Neither mode creates JPEG or
other temporary video frames, and the source MP4 is never transcoded or modified.

Downloaded binary used for local verification:

- Source: BtbN/FFmpeg-Builds GitHub release `latest`
- Asset: `ffmpeg-master-latest-win64-lgpl.zip`
- Build/version: `N-125773-g7002e01c19-20260726`
- SHA-256: `593056977e17f97773dd81f538accdc3e720cb767a2e5014819238393790aa13`
- License: LGPL build of FFmpeg; BtbN build scripts are MIT licensed
- Official FFmpeg download page lists BtbN as a Windows executable build provider.

The downloaded archive and extracted binaries are intentionally ignored by git.
Set `NEON_FFMPEG` / `NEON_FFPROBE`, or `NEON_FFPLAY_PATH` / `NEON_FFPROBE_PATH`, to verified executable paths, or place the checked BtbN
archive contents at:

`third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffmpeg.exe`

`third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffprobe.exe`

`third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffplay.exe`
