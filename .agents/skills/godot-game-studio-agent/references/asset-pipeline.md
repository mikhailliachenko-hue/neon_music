# Godot Asset Pipeline

Read this reference only when generating, importing, replacing, or binding runtime art.

## Asset record

Before integration, record purpose and gameplay scale, source or generation method, license/attribution, source and runtime paths, relevant import settings, runtime binding, and temporary replacement status.

Create `docs/asset-list.md` only when the project starts real asset production. Do not create it for an empty prototype.

## Workflow

1. Define the asset's gameplay job and target dimensions before generation or download.
2. Keep editable source material separate from runtime imports when both exist.
3. Use project-relative `res://` paths. Never bind scenes to temporary-generation folders or absolute machine paths.
4. Import in Godot and inspect warnings, dimensions, alpha, filtering, compression, animation frames, and memory impact.
5. Bind the asset to a real scene/resource and run that scene at gameplay scale.
6. Capture rendered evidence. File presence and successful import do not prove visual acceptance.

## Readability and replacement

- Critical actors, hazards, rewards, and interactables need distinct silhouette, value, or motion—not color alone.
- UI art must be checked at the smallest supported viewport and scale setting.
- Pixel art should use explicit filtering and integer-scale assumptions where appropriate.
- Replacing an asset must preserve or deliberately update dependent regions, pivots, collisions, animation names, and material parameters.
- Do not overwrite existing project art unless the user explicitly requested replacement.

Use Godot's [stable asset-pipeline documentation](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/index.html) matching the project version. Treat generated assets like third-party assets: provenance and permission still need to be recorded.
