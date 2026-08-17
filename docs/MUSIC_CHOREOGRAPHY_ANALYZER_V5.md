# Music-aware choreography analyzer V5

## Outcome

The analyzer is no longer only an onset-to-lane converter. It now builds a
hierarchical musical representation and uses it during movement selection:

1. beat, downbeat and meter;
2. four subdivisions per beat and multi-band accent type;
3. beat-synchronous energy, bass, drums, brightness, harmony change,
   syncopation and movement intensity;
4. bar-level novelty, repeated-form labels and functional sections;
5. drops, breaks, fills and peak accents;
6. per-section and per-phrase movement targets;
7. data-dependent candidate scoring and adaptive note density.

The original signal-based timing remains the fallback. When `madmom` is
installed, its joint RNN/DBN beat/downbeat tracker becomes the primary meter
evidence only when its tempo agrees with the rhythm-grid estimate. This
prevents silent half/double-tempo failures.

## Research translated into the implementation

- Dynamic-programming beat tracking combines onset strength, tempo estimation
  and pulse-consistent peak selection. This remains the robust fallback:
  <https://librosa.org/doc/latest/generated/librosa.beat.beat_track.html>
- Joint beat/downbeat tracking benefits from modeling the two tasks together.
  The optional backend follows Böck, Krebs and Widmer's RNN/DBN approach:
  <https://madmom.readthedocs.io/en/v0.16/modules/features/downbeats.html>
- Musical structure is hierarchical and subjective; beat-aligned,
  application-dependent output is more useful than pretending one section
  labeling is ground truth:
  <https://transactions.ismir.net/articles/10.5334/tismir.54>
- Self-similarity plus novelty is a standard way to find perceptual section
  changes. V5 uses beat-synchronous chroma, MFCC/timbre and energy vectors,
  then bar-aligned contextual novelty:
  <https://www.audiolabs-erlangen.de/resources/MIR/FMP/C4/C4S4_NoveltySegmentation.html>
- AIST++/FACT shows that music-conditioned dance needs long-range
  cross-modal context rather than isolated beat reactions:
  <https://arxiv.org/abs/2101.08779>
- Bailando's choreographic memory and beat-alignment reward motivate the
  reusable movement library plus explicit music-alignment score:
  <https://arxiv.org/abs/2203.13055>
- EDGE demonstrates that musical conditioning, temporal continuity and
  physical contact consistency all matter to perceived quality:
  <https://openaccess.thecvf.com/content/CVPR2023/papers/Tseng_EDGE_Editable_Dance_Generation_From_Music_CVPR_2023_paper.pdf>
- The all-in-one structure work demonstrates that jointly predicting beats,
  downbeats and functional sections lets the tasks reinforce one another:
  <https://arxiv.org/abs/2307.16425>
- Time-based Chart Partitioning shows that onset precision alone is not enough:
  short-window pattern coherence must be evaluated explicitly. V4 therefore
  scores local pickup/payoff patterns instead of emitting isolated strong hits:
  <https://ojs.aaai.org/index.php/AIIDE/article/view/36808>
- Danceba's phase-aware representation and separate upper/lower-body modeling
  motivate `phase_preference` and body counterpoint rather than treating every
  spectral accent as the same full-body action:
  <https://openaccess.thecvf.com/content/ICCV2025/html/Fan_Align_Your_Rhythm_Generating_Highly_Aligned_Dance_Poses_with_Gating-Enhanced_ICCV_2025_paper.html>
- Atomic-movement planning separates symbolic movement type/duration/timing
  from final motion synthesis. This matches the project's movement-event
  contract and supports explicit, editable mechanics such as pickup-to-drop:
  <https://arxiv.org/abs/2607.13978>

## New metadata

`beat_grid.json` now includes:

- `neural_meter`: availability, agreement, meter, coverage and beat evidence;
- `beat_features`: one descriptor per canonical beat;
- `sections`: bar-aligned roles and `movement_targets`;
- `musical_events`: accents, fills, drops, breaks and boundaries;
- `music_expression`: complete analysis plus summary.

Phrase-grid entries receive `section_role`, `section_energy_role`,
`music_targets`, and an accent curve. Movement events record the exact
`music_accent`, `music_accent_type`, `music_energy`, and `music_complexity`
that influenced their selection.

## Installation and controls

Base installation:

```powershell
python -m pip install -r requirements.txt
```

Neural downbeat/meter enhancement:

```powershell
python -m pip install -r requirements-advanced.txt
```

The command line enables the neural backend by default and falls back safely:

```powershell
python scripts/python/audio_analyzer.py --audio "assets/audio/Iron & Ash.mp3"
python scripts/python/audio_analyzer.py --audio "assets/audio/Iron & Ash.mp3" --no-neural-meter
```

The GUI automatically passes the original full mix to structure analysis while
the separated bass/drums mix continues to drive precise rhythmic onsets.

## Acceptance evidence

For the active `assets/audio/audio.wav`, the full Demucs path now emits Beat
Grid V2 directly: 403 raw detected beats, 425 canonical beats and 98.66%
detected coverage at 143.555 BPM. The normal V4 profile produces one selected
pickup-to-drop phrase, mean body-counterpoint fit 0.73, 31 compound movements,
zero deterministic repairs and zero hard choreography errors. Two complete
Analyzer runs are byte-identical after temporary Demucs paths are normalized
to the original source audio.
