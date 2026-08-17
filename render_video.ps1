param(
    [string]$Godot = "godot",
    [string]$Audio = "",
    [int]$FixedFps = 60,
    [string]$Resolution = "2560x1440",
    [string]$Output = "output\renders\output.avi"
)

$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $project

if ([string]::IsNullOrWhiteSpace($Audio)) {
    $Audio = Join-Path $project "assets\audio\audio.wav"
} elseif (-not [System.IO.Path]::IsPathRooted($Audio)) {
    $Audio = Join-Path (Get-Location) $Audio
}

if (-not [System.IO.Path]::IsPathRooted($Output)) {
    $Output = Join-Path $project $Output
}
$outputDir = Split-Path -Parent $Output
if (-not [string]::IsNullOrWhiteSpace($outputDir)) {
    New-Item -ItemType Directory -Force $outputDir | Out-Null
}

if (-not (Test-Path -LiteralPath $Audio -PathType Leaf)) {
    throw "Audio file is missing: $Audio"
}

$pythonCandidates = @(
    (Join-Path $project ".venv\Scripts\python.exe"),
    (Join-Path (Split-Path -Parent $project) ".venv\Scripts\python.exe"),
    "python"
)
$Python = $pythonCandidates | Where-Object { $_ -eq "python" -or (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -First 1

& $Python (Join-Path $project "scripts\python\audio_analyzer.py") --audio "$Audio"
& $Godot --path $project --editor --quit-after 2
& $Godot --rendering-driver vulkan --path $project --resolution $Resolution --write-movie $Output --fixed-fps $FixedFps -- "--audio=$Audio" "--render-clock=frame" "--clock-fps=$FixedFps"
