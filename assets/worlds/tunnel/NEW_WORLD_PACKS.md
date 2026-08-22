# Curated CC0 world packs

The production tunnel imports only the GLB modules referenced by the explicit
`TunnelWorldAssetSet` resources. Original filenames are preserved so a pack can
be refreshed without changing runtime code.

| Local folder | Official source | Used for |
| --- | --- | --- |
| `kenney_space_station/` | https://kenney.nl/assets/space-station-kit | Orbital Concourse, Zero-G Cargo |
| `kenney_space_kit/` | https://kenney.nl/assets/space-kit | Lunar Crystal Run, Monorail Nexus, Hangar Core |
| `kenney_retro_urban/` | https://kenney.nl/assets/retro-urban-kit | Retro Rooftops, Scaffold Rush |
| `kenney_nature_crystal/` | https://kenney.nl/assets/nature-kit | Asteroid Temple rock modules |

All four source packs are published under CC0. Each curated folder keeps the
pack's original `LICENSE.txt`. The central gameplay envelope is never authored
inside these GLB files: `TunnelSegment` fits paired architecture outside the
safe lane, while gates use the existing overhead/opening profile.
