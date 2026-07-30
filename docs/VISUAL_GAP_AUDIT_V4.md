# Visual Gap Audit V4

Date: 2026-07-30

## Sources inspected

- `output/renders/vertical_slice_choreo_v3_qa.avi`
- `output/renders/vertical_slice_choreo_v3_clean.avi`
- `output/previews/vertical_slice_choreo_v3/`
- `assets/images/reference/DANCE_MODE_#16___Interactive_Immersive_Warm_Up___Full_Body_Cardio.mp4`
- reference stills in `assets/images/reference/screenshots/`
- cue mapping, renderer scene, procedural cue meshes, decals, materials and MP4 backend

## Findings

### Lane placement and contact

The previous tap-cue formula produced X centers `[-0.975, 0.575, 2.125, 3.675]`, while receptors and the four 2-unit lanes use `[-3, -1, 1, 3]`. Thus three cues were systematically shifted and the rightmost cue approached the road boundary. Tap cue Y was close to the road but its visual pivot was implicit. Wide cues also compensated using the old offset, making their center inconsistent.

V4 establishes one contract: lane centers `[-3,-1,1,3]`, lane width `2.0`, cue width ratio `0.86`, road contact `Y=-1.72`, ground offset `0.045`, center-bottom pivot convention, spawn depth derived from unchanged hit time, and hit depth `Z=0`.

### Cue readability and orientation

- Step pads were the clearest cues, but the panel/footprint looked flatter and less grounded than the reference.
- Jump was a wide low box and could be confused with a lane divider at distance.
- Punch used a small sphere with weak frontal mass.
- Duck/squat was a floating bar without enough “clear space below” framing.
- Lean/sweep was a vertical slab; direction was weak.
- Left/right textures were selected by lane group rather than explicit foot metadata. This is fragile for mirrored choreography. V4 removes negative-scale mirroring and supplies an adjacent orientation test scene; explicit variants remain the preferred path.

### Execution zone and hit feedback

The old receptors were four thin outlines. The judgment plane was not visually dominant, and movie-safe rendering skipped the most noticeable hit FX. Consequently a hit often read as cue disappearance rather than execution. V4 adds large translucent pads, a permanent judgment line, lane-local emissive spike and a 150 ms afterglow.

### Road, background and depth

The current clean preview is dominated by black negative space. The road has good perspective lines but behaves like a separate dark plane; the MP4/reference has a continuous horizon and brighter lateral support. Far cues are thin and lose contrast. V4 adds road micro-lines, execution-zone contrast, edge/horizon contribution, approach energy and section-controlled emissive staging. Existing MP4 loading/playback is untouched.

### Composition gap versus reference

The largest gaps are, in order: incorrect lane placement; weak execution deck; insufficient cue silhouettes; black/empty upper frame; weak hit confirmation; and limited section-to-section intensity change. The reference has a broad readable stage, strong horizon color mass, chunky cue silhouettes, luminous foreground pads and obvious hit bursts. V4 addresses the first five as an additive renderer layer without changing timing or data contracts.
