param(
    [string]$ProjectPath = (Get-Location).Path,
    [string]$ProjectName = "Godot Game",
    [string]$Genre = "custom",
    [string]$TargetPlatform = "desktop",
    [string]$Perspective = "2D"
)

$ErrorActionPreference = "Stop"
$script:Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Write-NewTextFile {
    param([string]$Path, [string]$Value)
    if (Test-Path -LiteralPath $Path) {
        Write-Host "Exists, preserved: $Path"
        return $false
    }
    [System.IO.File]::WriteAllText($Path, $Value, $script:Utf8NoBom)
    Write-Host "Created: $Path"
    return $true
}

function ConvertTo-GodotString {
    param([string]$Value)
    return $Value.Replace('\', '\\').Replace('"', '\"').Replace("`r", " ").Replace("`n", " ")
}

$pathExisted = Test-Path -LiteralPath $ProjectPath
if (-not $pathExisted) { New-Item -ItemType Directory -Path $ProjectPath | Out-Null }
$resolvedProject = (Resolve-Path -LiteralPath $ProjectPath).ProviderPath
$projectFile = Join-Path $resolvedProject "project.godot"

if ($pathExisted -and -not (Test-Path -LiteralPath $projectFile)) {
    $entries = @(Get-ChildItem -LiteralPath $resolvedProject -Force -ErrorAction Stop)
    if ($entries.Count -gt 0) { throw "Refusing to create a Godot project in a non-empty directory without project.godot: $resolvedProject" }
}

$scenesDir = Join-Path $resolvedProject "scenes"
$scriptsDir = Join-Path $resolvedProject "scripts"
$docsDir = Join-Path $resolvedProject "docs"
$validationDir = Join-Path $resolvedProject "artifacts\validation"
foreach ($dir in @($scenesDir, $scriptsDir, $docsDir, $validationDir)) {
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
}

$safeName = ConvertTo-GodotString $ProjectName
Write-NewTextFile -Path $projectFile -Value @"
; Minimal Godot 4.x project created by godot-game-studio-agent.
config_version=5

[application]

config/name="$safeName"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.0")

[display]

window/size/viewport_width=1280
window/size/viewport_height=720
window/size/window_width_override=1280
window/size/window_height_override=720

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"@ | Out-Null

Write-NewTextFile -Path (Join-Path $scenesDir "main.tscn") -Value @"
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/main.gd" id="1_main"]

[node name="Main" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
script = ExtResource("1_main")

[node name="Background" type="ColorRect" parent="."]
layout_mode = 1
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
color = Color(0.035, 0.047, 0.075, 1)

[node name="Title" type="Label" parent="."]
layout_mode = 0
offset_left = 40.0
offset_top = 36.0
offset_right = 760.0
offset_bottom = 82.0
theme_override_font_sizes/font_size = 28
text = "$safeName — prototype ready"
"@ | Out-Null

Write-NewTextFile -Path (Join-Path $scriptsDir "main.gd") -Value @'
extends Control

func _ready() -> void:
    print("GODOT_GAME_STUDIO_READY")
'@ | Out-Null

$date = Get-Date -Format "yyyy-MM-dd"
Write-NewTextFile -Path (Join-Path $docsDir "game-brief.md") -Value @"
# Game Brief

Updated: $date

## Player and experience hypothesis

- Project: $ProjectName
- Genre: $Genre
- Target platform: $TargetPlatform
- Perspective: $Perspective
- Intended player: Unknown
- Hypothesis: Unknown
- Observable proof: Unknown
- Observable failure: Unknown

## Core loop and learning path

- Goal: Unknown
- Core verb: Unknown
- Obstacle or decision: Unknown
- Feedback: Unknown
- Success/failure and retry: Unknown
- What the player sees first: Unknown
- First prompted use: Unknown
- First unprompted repetition: Unknown
- Changed-context application: Unknown

## Target and budgets

- Target device: Unknown
- Resolution: 1280x720 prototype baseline
- Target FPS / frame time: Unknown
- Memory budget: Unknown
- Startup budget: Unknown
- Scene-transition budget: Unknown

## Constraints and unknowns

- Must keep: one runnable entry scene and one evidence-backed core behavior
- Explicitly out of scope: multiplayer, LiveOps, monetization, and content scaling until separately approved
- Unknowns: audience, controls, art direction, audio direction, accessibility needs, release target
"@ | Out-Null

Write-NewTextFile -Path (Join-Path $docsDir "dev-plan.md") -Value @"
# Development Plan

Updated: $date

## Current experiment

- Hypothesis: Unknown
- Playable case: Unknown
- Proof: Unknown
- Failure: Unknown
- Decision: pending
- Next scope if proven: Unknown

## Core

| Work | Purpose | Proof | Kill condition | Status |
| --- | --- | --- | --- | --- |
| Define and implement one playable behavior | Test the experience hypothesis | L2 rendered observation and L3 input evidence | Remove or revise if the intended behavior is not readable or useful | pending |

## Support

- None committed.

## Wishlist

- None committed.

## Latest evidence

- Highest level: L0 SOURCE_INSPECTED
- Receipt: Not created
- Open failures: First playable not implemented or observed

## Next decision

- Define the player-facing hypothesis, smallest playable case, proof, and failure before expanding scope.
"@ | Out-Null

Write-Host "Godot project ready: $resolvedProject"
