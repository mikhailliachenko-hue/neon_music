AI exchange workflow

1. Put the track you want to analyze into ai_exchange/INPUT.
2. Upload ai_exchange/INPUT/NEON_CHOREO_PROMPT.txt and the track to ChatGPT.
3. Ask ChatGPT to return one file only: neon_track.json.
4. Put the returned neon_track.json into ai_exchange/OUTPUT.
5. Run:

python scripts/python/import_ai_neon_track.py

The importer writes one project file:

output/neon_track.json

Do not copy beatmap.json, beat_grid.json, beatmap_v4.json, beat_grid_v2.json, or combo.srt into the project for the normal workflow.
