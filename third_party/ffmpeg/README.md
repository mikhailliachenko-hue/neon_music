# FFmpeg dependency for MP4 background playback

The MP4 background backend uses a local FFmpeg executable to decode
`background/reference_fullhd.mp4` into a transient `user://` JPEG frame. The
source MP4 is not transcoded or modified.

Downloaded binary used for local verification:

- Source: BtbN/FFmpeg-Builds GitHub release `latest`
- Asset: `ffmpeg-master-latest-win64-lgpl.zip`
- Build/version: `N-125773-g7002e01c19-20260726`
- SHA-256: `593056977e17f97773dd81f538accdc3e720cb767a2e5014819238393790aa13`
- License: LGPL build of FFmpeg; BtbN build scripts are MIT licensed
- Official FFmpeg download page lists BtbN as a Windows executable build provider.

The downloaded archive and extracted binaries are intentionally ignored by git.
Set `NEON_FFMPEG` to a verified `ffmpeg.exe` path, or place the checked BtbN
archive contents at:

`third_party/ffmpeg/ffmpeg-master-latest-win64-lgpl/bin/ffmpeg.exe`
