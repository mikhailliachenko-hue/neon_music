param(
    [string]$ProjectPath = (Get-Location).Path,
    [string]$GodotPath = "",
    [string]$CodexConfig = "",
    [switch]$AsJson
)

$ErrorActionPreference = "Stop"

function Resolve-GodotExecutable {
    param([string]$ExplicitPath)
    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($candidate in @($ExplicitPath, $env:GODOT4_PATH, $env:GODOT_PATH)) { if ($candidate) { $candidates.Add($candidate) } }
    foreach ($name in @("godot4", "godot")) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $candidates.Add($command.Source) }
    }
    $wingetRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path -LiteralPath $wingetRoot) {
        Get-ChildItem -LiteralPath $wingetRoot -Directory -Filter "GodotEngine.GodotEngine_*" -ErrorAction SilentlyContinue |
            ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -File -Filter "Godot*_console.exe" -ErrorAction SilentlyContinue } |
            ForEach-Object { $candidates.Add($_.FullName) }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { return (Resolve-Path -LiteralPath $candidate).ProviderPath }
    }
    return $null
}

function Resolve-CodexConfigPath {
    param([string]$ExplicitPath)
    if ($ExplicitPath) { return $ExplicitPath }
    if ($env:CODEX_HOME) { return (Join-Path $env:CODEX_HOME "config.toml") }
    return (Join-Path $env:USERPROFILE ".codex\config.toml")
}

$resolvedProject = $null
try { $resolvedProject = (Resolve-Path -LiteralPath $ProjectPath).ProviderPath } catch { $resolvedProject = [IO.Path]::GetFullPath($ProjectPath) }
$projectExists = Test-Path -LiteralPath (Join-Path $resolvedProject "project.godot") -PathType Leaf
$resolvedGodot = Resolve-GodotExecutable $GodotPath
$godotVersion = $null
$godot4 = $false
if ($resolvedGodot) {
    $godotVersion = ((& $resolvedGodot --version 2>&1) -join " ").Trim()
    $godot4 = ($LASTEXITCODE -eq 0 -and $godotVersion -match '^4\.')
}

$resolvedConfig = Resolve-CodexConfigPath $CodexConfig
$configExists = Test-Path -LiteralPath $resolvedConfig -PathType Leaf
$configValid = $null
$godotiqConfigured = $false
$configuredRoot = $null
$python = Get-Command python -ErrorAction SilentlyContinue
if ($configExists -and $python) {
    $code = 'import json,pathlib,sys,tomllib; d=tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); g=d.get("mcp_servers",{}).get("godotiq",{}); print(json.dumps({"configured":bool(g),"root":g.get("env",{}).get("GODOTIQ_PROJECT_ROOT")},ensure_ascii=False))'
    try {
        $parsedText = (& $python.Source -c $code $resolvedConfig 2>$null) -join ""
        if ($LASTEXITCODE -eq 0) {
            $parsed = $parsedText | ConvertFrom-Json
            $configValid = $true
            $godotiqConfigured = [bool]$parsed.configured
            $configuredRoot = $parsed.root
        } else { $configValid = $false }
    } catch { $configValid = $false }
}

$uvx = Get-Command uvx -ErrorAction SilentlyContinue
$result = [ordered]@{
    project_path = $resolvedProject
    project_godot = $projectExists
    godot_path = $resolvedGodot
    godot_version = $godotVersion
    godot_4_x = $godot4
    uvx_path = if ($uvx) { $uvx.Source } else { $null }
    python_path = if ($python) { $python.Source } else { $null }
    codex_config = $resolvedConfig
    codex_config_exists = $configExists
    codex_config_valid = $configValid
    godotiq_configured = $godotiqConfigured
    godotiq_project_root = $configuredRoot
    godotiq_project_matches = ($configuredRoot -and ([IO.Path]::GetFullPath($configuredRoot) -eq [IO.Path]::GetFullPath($resolvedProject)))
    usable = ($projectExists -and $godot4)
}

if ($AsJson) { $result | ConvertTo-Json -Depth 5 } else {
    foreach ($entry in $result.GetEnumerator()) {
        "{0,-28} {1}" -f $entry.Key, $(if ($null -eq $entry.Value) { "not_checked" } else { $entry.Value })
    }
}
if (-not $result.usable) { exit 1 }
