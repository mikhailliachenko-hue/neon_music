param(
    [string]$ProjectPath = (Get-Location).Path,
    [string]$CodexConfig = "",
    [switch]$InstallGodotIQ,
    [switch]$InstallAddon
)

$ErrorActionPreference = "Stop"
$script:Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$script:BeginMarker = "# BEGIN managed by godot-game-studio-agent"
$script:EndMarker = "# END managed by godot-game-studio-agent"

function Resolve-CodexConfigPath {
    param([string]$ExplicitPath)
    if ($ExplicitPath) { return [IO.Path]::GetFullPath($ExplicitPath) }
    if ($env:CODEX_HOME) { return (Join-Path $env:CODEX_HOME "config.toml") }
    return (Join-Path $env:USERPROFILE ".codex\config.toml")
}

function ConvertTo-TomlString {
    param([string]$Value)
    return '"' + $Value.Replace('\', '\\').Replace('"', '\"').Replace("`t", '\t').Replace("`r", '\r').Replace("`n", '\n') + '"'
}

function Remove-ManagedRanges {
    param([string[]]$Lines)
    $output = [System.Collections.Generic.List[string]]::new()
    $inside = $false
    foreach ($line in $Lines) {
        if ($line.Trim() -eq $script:BeginMarker) { $inside = $true; continue }
        if ($inside -and $line.Trim() -eq $script:EndMarker) { $inside = $false; continue }
        if (-not $inside) { $output.Add($line) }
    }
    if ($inside) { throw "Codex config contains an unterminated managed GodotIQ block." }
    return $output.ToArray()
}

function Remove-GodotIqTables {
    param([string[]]$Lines)
    $output = [System.Collections.Generic.List[string]]::new()
    $skip = $false
    foreach ($line in $Lines) {
        $trimmed = $line.Trim()
        $isHeader = $trimmed -match '^\[\[?.+\]\]?(?:\s*#.*)?$'
        $isGodotIq = $trimmed -match '^\[mcp_servers\.godotiq(?:\.[^\]]+)?\](?:\s*#.*)?$'
        if ($isGodotIq) { $skip = $true; continue }
        if ($skip -and $isHeader) { $skip = $false }
        if (-not $skip) { $output.Add($line) }
    }
    return $output.ToArray()
}

function Invoke-TomlValidation {
    param([string]$Path, [string]$ExpectedRoot = "")
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) { throw "Python 3.11+ is required to validate Codex TOML safely." }
    & $python.Source -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)'
    if ($LASTEXITCODE -ne 0) { throw "Python 3.11+ is required because setup uses the standard tomllib parser." }
    $code = if ($ExpectedRoot) {
        'import pathlib,sys,tomllib; d=tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); g=d["mcp_servers"]["godotiq"]; ok=g.get("command")=="uvx" and g.get("args")==["godotiq"] and g.get("env",{}).get("GODOTIQ_PROJECT_ROOT")==sys.argv[2]; raise SystemExit(0 if ok else 3)'
    } else {
        'import pathlib,sys,tomllib; tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))'
    }
    if ($ExpectedRoot) { & $python.Source -c $code $Path $ExpectedRoot } else { & $python.Source -c $code $Path }
    if ($LASTEXITCODE -ne 0) { throw "TOML validation failed for $Path" }
}

$resolvedProject = (Resolve-Path -LiteralPath $ProjectPath).ProviderPath
if (-not (Test-Path -LiteralPath (Join-Path $resolvedProject "project.godot") -PathType Leaf)) { throw "No project.godot found at $resolvedProject" }
$uvx = Get-Command uvx -ErrorAction SilentlyContinue
if (-not $uvx) { throw "uvx was not found; GodotIQ cannot be configured as command = 'uvx'." }

if ($InstallGodotIQ) {
    $env:PYTHONUTF8 = "1"
    & $uvx.Source godotiq --help | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "GodotIQ availability check failed." }
}
if ($InstallAddon) {
    $env:PYTHONUTF8 = "1"
    & $uvx.Source godotiq install-addon $resolvedProject
    if ($LASTEXITCODE -ne 0) { throw "GodotIQ addon installation failed." }
}

$resolvedConfig = Resolve-CodexConfigPath $CodexConfig
$configDir = Split-Path -Parent $resolvedConfig
if (-not (Test-Path -LiteralPath $configDir)) { New-Item -ItemType Directory -Path $configDir | Out-Null }
$existing = ""
if (Test-Path -LiteralPath $resolvedConfig -PathType Leaf) {
    Invoke-TomlValidation -Path $resolvedConfig
    $existing = [IO.File]::ReadAllText($resolvedConfig)
}
$newline = if ($existing.Contains("`r`n")) { "`r`n" } else { "`n" }
$lines = if ($existing) { $existing -split "\r?\n" } else { @() }
$withoutManaged = Remove-ManagedRanges $lines
$withoutTables = Remove-GodotIqTables $withoutManaged
$base = ($withoutTables -join $newline).TrimEnd()
$projectToml = ConvertTo-TomlString $resolvedProject
$block = @($script:BeginMarker, "[mcp_servers.godotiq]", 'command = "uvx"', 'args = ["godotiq"]', "", "[mcp_servers.godotiq.env]", "GODOTIQ_PROJECT_ROOT = $projectToml", $script:EndMarker) -join $newline
$candidate = $(if ($base) { $base + $newline + $newline } else { "" }) + $block + $newline

if ($candidate -ceq $existing) {
    Write-Host "GodotIQ MCP configuration already matches: $resolvedConfig"
    exit 0
}

$tempPath = Join-Path $configDir (".{0}.tmp" -f [IO.Path]::GetRandomFileName())
[IO.File]::WriteAllText($tempPath, $candidate, $script:Utf8NoBom)
try {
    Invoke-TomlValidation -Path $tempPath -ExpectedRoot $resolvedProject
    if (Test-Path -LiteralPath $resolvedConfig -PathType Leaf) {
        $backup = "$resolvedConfig.bak-$(Get-Date -Format 'yyyyMMdd-HHmmssfff')"
        [IO.File]::Replace($tempPath, $resolvedConfig, $backup, $true)
        Write-Host "Backup written: $backup"
    } else {
        [IO.File]::Move($tempPath, $resolvedConfig)
    }
} finally {
    if (Test-Path -LiteralPath $tempPath) { Remove-Item -LiteralPath $tempPath -Force }
}
Write-Host "Configured one GodotIQ MCP server in $resolvedConfig"
Write-Host "Restart Codex to load the updated MCP configuration."
