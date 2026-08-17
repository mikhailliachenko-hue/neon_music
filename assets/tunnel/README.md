# Tunnel modular assets

This is the canonical asset intake for the Dance Mode tunnel. Imported source
packs stay intact; small wrapper scenes normalize their scale, pivot and safe
placement before the runtime AssetRegistry uses them.

- `environment/`: HDRI and large environment/support modules.
- `walls/`, `floors/`, `rings/`, `panels/`: structural modules.
- `decorations/`, `particles/`: optional detail modules.
- `materials/`, `themes/`: material references and visual-style documentation.

Quaternius Modular Sci-Fi MegaKit modules should be placed in matching folders
and registered in `asset_registry.tres`. The included simple scenes are fallback
placeholders, not final complex geometry.
