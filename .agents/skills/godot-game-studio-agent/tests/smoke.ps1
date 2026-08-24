param(
    [string]$GodotPath = ""
)

$ErrorActionPreference = "Stop"
$script:Utf8NoBom = [Text.UTF8Encoding]::new($false)
$skillRoot = Split-Path -Parent $PSScriptRoot
$scripts = Join-Path $skillRoot "scripts"
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$python = (Get-Command python -ErrorAction Stop).Source
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
$workRoot = Join-Path $tempBase ("godot-skill-smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $workRoot | Out-Null
$script:Passed = 0

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
    $script:Passed++
}

function Invoke-ChildScript {
    param([string]$ScriptPath, [string[]]$Arguments = @())
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $pwsh
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.ArgumentList.Add("-NoProfile")
    $psi.ArgumentList.Add("-File")
    $psi.ArgumentList.Add($ScriptPath)
    foreach ($argument in $Arguments) { $psi.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdout = $process.StandardOutput.ReadToEndAsync()
    $stderr = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(180000)) {
        try { $process.Kill($true) } catch {}
        throw "Child script timed out: $ScriptPath"
    }
    return [pscustomobject]@{
        ExitCode = $process.ExitCode
        StdOut = $stdout.GetAwaiter().GetResult()
        StdErr = $stderr.GetAwaiter().GetResult()
    }
}

function Get-LatestReceipt {
    param([string]$ProjectPath)
    $receipt = Get-ChildItem -LiteralPath (Join-Path $ProjectPath "artifacts\validation") -Filter "receipt.json" -File -Recurse |
        Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $receipt) { throw "No validation receipt found for $ProjectPath" }
    return (Get-Content -LiteralPath $receipt.FullName -Raw | ConvertFrom-Json)
}

function New-FixtureProject {
    param([string]$Name)
    $path = Join-Path $workRoot $Name
    & (Join-Path $scripts "start-godot-project.ps1") -ProjectPath $path -ProjectName $Name -Genre "platformer" -TargetPlatform "desktop" -Perspective "2D"
    return $path
}

function Assert-TomlRoot {
    param([string]$ConfigPath, [string]$ExpectedRoot)
    $code = 'import pathlib,sys,tomllib; d=tomllib.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); g=d["mcp_servers"]["godotiq"]; print(g["env"]["GODOTIQ_PROJECT_ROOT"]); raise SystemExit(0 if g["env"]["GODOTIQ_PROJECT_ROOT"]==sys.argv[2] else 4)'
    $actual = (& $python -c $code $ConfigPath $ExpectedRoot) -join ""
    Assert-True ($LASTEXITCODE -eq 0) "TOML root should decode to the exact project path; got '$actual'."
}

try {
    Write-Host "[1/6] Bootstrap and preservation"
    $project = New-FixtureProject "中文 游戏 #1"
    foreach ($relative in @("project.godot", "scenes\main.tscn", "scripts\main.gd", "docs\game-brief.md", "docs\dev-plan.md", "artifacts\validation")) {
        Assert-True (Test-Path -LiteralPath (Join-Path $project $relative)) "Bootstrap should create $relative"
    }
    $topNames = @(Get-ChildItem -LiteralPath $project -Force | Select-Object -ExpandProperty Name | Sort-Object)
    Assert-True (($topNames -join '|') -eq 'artifacts|docs|project.godot|scenes|scripts') "Bootstrap should create only the minimal top-level shape."
    $protected = @("project.godot", "scenes\main.tscn", "scripts\main.gd", "docs\game-brief.md", "docs\dev-plan.md")
    $before = @{}; foreach ($relative in $protected) { $before[$relative] = (Get-FileHash -LiteralPath (Join-Path $project $relative) -Algorithm SHA256).Hash }
    & (Join-Path $scripts "start-godot-project.ps1") -ProjectPath $project -ProjectName "Changed name" | Out-Null
    foreach ($relative in $protected) { Assert-True ((Get-FileHash -LiteralPath (Join-Path $project $relative) -Algorithm SHA256).Hash -eq $before[$relative]) "Existing $relative must be preserved." }

    Write-Host "[2/6] Environment and clean L1 validation"
    $envArgs = @("-ProjectPath", $project, "-AsJson")
    if ($GodotPath) { $envArgs += @("-GodotPath", $GodotPath) }
    $envResult = Invoke-ChildScript (Join-Path $scripts "check-godot-env.ps1") $envArgs
    Assert-True ($envResult.ExitCode -eq 0) "Environment check should pass: $($envResult.StdErr)"
    $envJson = $envResult.StdOut | ConvertFrom-Json
    Assert-True ($envJson.godot_4_x -eq $true) "Environment check should resolve Godot 4.x."
    $validateArgs = @("-ProjectPath", $project, "-TimeoutSeconds", "30")
    if ($GodotPath) { $validateArgs += @("-GodotPath", $GodotPath) }
    $clean = Invoke-ChildScript (Join-Path $scripts "validate-godot-project.ps1") $validateArgs
    Assert-True ($clean.ExitCode -eq 0) "Clean project should pass L1: $($clean.StdErr) $($clean.StdOut)"
    $receipt = Get-LatestReceipt $project
    Assert-True ($receipt.schema -eq "godot-game-validation.v1") "Receipt schema should be stable."
    Assert-True ($receipt.highest_evidence.level -eq "L1") "Clean default validation should reach L1."
    Assert-True ($receipt.checks.graphical_runtime.status -eq "not_run") "L2 must remain not_run."
    Assert-True ($receipt.checks.input_replay.status -eq "not_run") "L3 must remain not_run."
    Assert-True ($receipt.checks.export_black_box.status -eq "not_run") "L4 must remain not_run without export."

    Write-Host "[3/6] MCP TOML replacement and idempotence"
    $configDir = Join-Path $workRoot "codex config"
    New-Item -ItemType Directory -Path $configDir | Out-Null
    $config = Join-Path $configDir "config.toml"
    [IO.File]::WriteAllText($config, "model = `"test`"`n`n[mcp_servers.other]`ncommand = `"other`"`n", $script:Utf8NoBom)
    $setupArgs = @("-ProjectPath", $project, "-CodexConfig", $config)
    $setup = Invoke-ChildScript (Join-Path $scripts "setup-godot-mcp.ps1") $setupArgs
    Assert-True ($setup.ExitCode -eq 0) "MCP setup should succeed: $($setup.StdErr)"
    Assert-TomlRoot $config $project
    $content = [IO.File]::ReadAllText($config)
    Assert-True (([regex]::Matches($content, '(?m)^\[mcp_servers\.godotiq\]$')).Count -eq 1) "Config must contain one GodotIQ table."
    Assert-True ($content.Contains("[mcp_servers.other]")) "Unrelated MCP table must be preserved."
    $hashBefore = (Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash
    $backupsBefore = @(Get-ChildItem -LiteralPath $configDir -Filter "config.toml.bak-*" -File).Count
    $setupAgain = Invoke-ChildScript (Join-Path $scripts "setup-godot-mcp.ps1") $setupArgs
    Assert-True ($setupAgain.ExitCode -eq 0) "Second MCP setup should succeed."
    Assert-True ((Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash -eq $hashBefore) "Second MCP setup must not rewrite an identical config."
    Assert-True (@(Get-ChildItem -LiteralPath $configDir -Filter "config.toml.bak-*" -File).Count -eq $backupsBefore) "Second MCP setup must not create a backup."
    [IO.File]::WriteAllText($config, "[mcp_servers.godotiq]`ncommand=`"old`"`n`n[mcp_servers.godotiq.env]`nGODOTIQ_PROJECT_ROOT=`"C:\\old`"`n`n[mcp_servers.other]`ncommand=`"other`"`n", $script:Utf8NoBom)
    $replace = Invoke-ChildScript (Join-Path $scripts "setup-godot-mcp.ps1") $setupArgs
    Assert-True ($replace.ExitCode -eq 0) "Unmanaged GodotIQ table should be replaced."
    Assert-TomlRoot $config $project
    $content = [IO.File]::ReadAllText($config)
    Assert-True (([regex]::Matches($content, '(?m)^\[mcp_servers\.godotiq\]$')).Count -eq 1) "Replacement must leave one GodotIQ table."

    Write-Host "[4/6] Invalid TOML protection"
    [IO.File]::WriteAllText($config, "broken = [`n", $script:Utf8NoBom)
    $invalidHash = (Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash
    $invalid = Invoke-ChildScript (Join-Path $scripts "setup-godot-mcp.ps1") $setupArgs
    Assert-True ($invalid.ExitCode -ne 0) "Invalid existing TOML must be rejected."
    Assert-True ((Get-FileHash -LiteralPath $config -Algorithm SHA256).Hash -eq $invalidHash) "Rejected invalid TOML must remain byte-for-byte unchanged."

    Write-Host "[5/6] Failure injection"
    $parseProject = New-FixtureProject "parse-failure"
    [IO.File]::WriteAllText((Join-Path $parseProject "scripts\main.gd"), "extends Control`nfunc _ready( -> void:`n    pass`n", $script:Utf8NoBom)
    $args = @("-ProjectPath", $parseProject, "-TimeoutSeconds", "30"); if ($GodotPath) { $args += @("-GodotPath", $GodotPath) }
    $parseFailure = Invoke-ChildScript (Join-Path $scripts "validate-godot-project.ps1") $args
    Assert-True ($parseFailure.ExitCode -ne 0) "Injected GDScript parse error must fail validation."
    Assert-True ((Get-LatestReceipt $parseProject).overall_status -eq "fail") "Parse failure receipt must be fail."
    $resourceProject = New-FixtureProject "missing-resource"
    $scenePath = Join-Path $resourceProject "scenes\main.tscn"
    $sceneText = [IO.File]::ReadAllText($scenePath).Replace('res://scripts/main.gd', 'res://scripts/missing.gd')
    [IO.File]::WriteAllText($scenePath, $sceneText, $script:Utf8NoBom)
    $args = @("-ProjectPath", $resourceProject, "-TimeoutSeconds", "30"); if ($GodotPath) { $args += @("-GodotPath", $GodotPath) }
    Assert-True ((Invoke-ChildScript (Join-Path $scripts "validate-godot-project.ps1") $args).ExitCode -ne 0) "Missing resource must fail validation."
    $mainProject = New-FixtureProject "missing-main"
    $projectText = [IO.File]::ReadAllText((Join-Path $mainProject "project.godot")).Replace('res://scenes/main.tscn', 'res://scenes/missing.tscn')
    [IO.File]::WriteAllText((Join-Path $mainProject "project.godot"), $projectText, $script:Utf8NoBom)
    $args = @("-ProjectPath", $mainProject, "-TimeoutSeconds", "30"); if ($GodotPath) { $args += @("-GodotPath", $GodotPath) }
    Assert-True ((Invoke-ChildScript (Join-Path $scripts "validate-godot-project.ps1") $args).ExitCode -ne 0) "Missing main scene must fail validation."

    Write-Host "[6/6] Windows export and L4 black-box"
    $preset = @'
[preset.0]

name="Windows Desktop"
platform="Windows Desktop"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path=""
script_export_mode=2

[preset.0.options]

custom_template/debug=""
custom_template/release=""
debug/export_console_wrapper=1
binary_format/embed_pck=false
binary_format/architecture="x86_64"
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
'@
    [IO.File]::WriteAllText((Join-Path $project "export_presets.cfg"), $preset, $script:Utf8NoBom)
    $exportPath = Join-Path $workRoot "export output\smoke.exe"
    $exportArgs = @("-ProjectPath", $project, "-ExportPreset", "Windows Desktop", "-ExportPath", $exportPath, "-TimeoutSeconds", "60")
    if ($GodotPath) { $exportArgs += @("-GodotPath", $GodotPath) }
    $export = Invoke-ChildScript (Join-Path $scripts "validate-godot-project.ps1") $exportArgs
    Assert-True ($export.ExitCode -eq 0) "Export validation should pass: $($export.StdErr) $($export.StdOut)"
    $exportReceipt = Get-LatestReceipt $project
    Assert-True ($exportReceipt.checks.export_build.status -eq "pass") "Export build should pass."
    Assert-True ($exportReceipt.checks.export_black_box.status -eq "pass") "Exported executable should launch."
    Assert-True ($exportReceipt.highest_evidence.level -eq "L4") "Export validation should reach L4."

    Write-Host "PASS: $script:Passed assertions"
} finally {
    $resolvedWork = [IO.Path]::GetFullPath($workRoot)
    if ($resolvedWork.StartsWith($tempBase + '\', [StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolvedWork).StartsWith('godot-skill-smoke-')) {
        try { [IO.Directory]::Delete($resolvedWork, $true) } catch { Write-Warning "Temporary smoke directory remains: $resolvedWork" }
    }
}
