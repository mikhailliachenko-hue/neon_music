param(
    [string]$ProjectPath = (Get-Location).Path,
    [string]$GodotPath = "",
    [string]$Scene = "",
    [string]$ExportPreset = "",
    [string]$ExportPath = "",
    [string]$ArtifactRoot = "",
    [ValidateRange(5, 600)]
    [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$script:Utf8NoBom = [System.Text.UTF8Encoding]::new($false)

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
    throw "Godot executable not found. Pass -GodotPath or set GODOT4_PATH/GODOT_PATH."
}

function Invoke-CapturedProcess {
    param([string]$FilePath, [string[]]$Arguments, [int]$Timeout, [string]$LogPath)
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FilePath
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $psi.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $psi
    $startedAt = [DateTime]::UtcNow
    [void]$process.Start()
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $timedOut = -not $process.WaitForExit($Timeout * 1000)
    if ($timedOut) {
        try { $process.Kill($true) } catch {}
        [void]$process.WaitForExit(5000)
    }
    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    $combined = $stdout + $(if ($stdout -and $stderr) { "`n" } else { "" }) + $stderr
    [IO.File]::WriteAllText($LogPath, $combined, $script:Utf8NoBom)
    $patterns = '(?i)(SCRIPT ERROR|Parse Error|ERROR:|Failed loading|Cannot open|Invalid get index|Invalid call)'
    $errors = @($combined -split "\r?\n" | Where-Object { $_ -match $patterns } | Select-Object -Unique -First 20)
    $exitCode = if ($timedOut) { -1 } else { $process.ExitCode }
    return [ordered]@{
        command = @($FilePath) + $Arguments
        exit_code = $exitCode
        timed_out = $timedOut
        duration_ms = [int]([DateTime]::UtcNow - $startedAt).TotalMilliseconds
        log = $LogPath
        errors = $errors
        status = if (-not $timedOut -and $exitCode -eq 0 -and $errors.Count -eq 0) { "pass" } else { "fail" }
    }
}

$resolvedProject = (Resolve-Path -LiteralPath $ProjectPath).ProviderPath
if (-not (Test-Path -LiteralPath (Join-Path $resolvedProject "project.godot") -PathType Leaf)) { throw "No project.godot found at $resolvedProject" }
$resolvedGodot = Resolve-GodotExecutable $GodotPath
$godotVersion = ((& $resolvedGodot --version 2>&1) -join " ").Trim()
if ($LASTEXITCODE -ne 0 -or $godotVersion -notmatch '^4\.') { throw "Godot 4.x is required; found '$godotVersion'." }

if (-not $ArtifactRoot) { $ArtifactRoot = Join-Path $resolvedProject "artifacts\validation" }
if (-not [IO.Path]::IsPathRooted($ArtifactRoot)) { $ArtifactRoot = Join-Path $resolvedProject $ArtifactRoot }
if (-not (Test-Path -LiteralPath $ArtifactRoot)) { New-Item -ItemType Directory -Path $ArtifactRoot | Out-Null }
$runId = "{0}-{1}" -f ([DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")), ([guid]::NewGuid().ToString("N").Substring(0, 8))
$runDir = Join-Path (Resolve-Path -LiteralPath $ArtifactRoot).ProviderPath $runId
New-Item -ItemType Directory -Path $runDir | Out-Null

$gitCommit = $null
$gitDirty = $null
$git = Get-Command git -ErrorAction SilentlyContinue
if ($git) {
    $gitCommitText = (& $git.Source -C $resolvedProject rev-parse HEAD 2>$null) -join ""
    if ($LASTEXITCODE -eq 0) {
        $gitCommit = $gitCommitText.Trim()
        $gitDirty = ((& $git.Source -C $resolvedProject status --porcelain 2>$null) | Measure-Object).Count -gt 0
    }
}

$checks = [ordered]@{}
$checks.source_inspection = [ordered]@{ status = "pass"; level = "L0"; label = "SOURCE_INSPECTED"; project_file = (Join-Path $resolvedProject "project.godot") }
$checks.project_import = Invoke-CapturedProcess -FilePath $resolvedGodot -Arguments @("--headless", "--editor", "--path", $resolvedProject, "--quit") -Timeout $TimeoutSeconds -LogPath (Join-Path $runDir "project-import.log")
$runtimeArgs = @("--headless", "--path", $resolvedProject, "--quit-after", "120")
if ($Scene) { $runtimeArgs += $Scene }
$checks.headless_runtime = Invoke-CapturedProcess -FilePath $resolvedGodot -Arguments $runtimeArgs -Timeout $TimeoutSeconds -LogPath (Join-Path $runDir "headless-runtime.log")
$checks.graphical_runtime = [ordered]@{ status = "not_run"; level = "L2"; label = "GRAPHICAL_RUNTIME"; reason = "Requires rendered observation through an editor or graphical automation tool." }
$checks.input_replay = [ordered]@{ status = "not_run"; level = "L3"; label = "INPUT_REPLAY"; reason = "Requires named input actions and visible state assertions." }
$checks.export_build = [ordered]@{ status = "not_run"; reason = "No -ExportPreset was provided." }
$checks.export_black_box = [ordered]@{ status = "not_run"; level = "L4"; label = "EXPORTED_BLACK_BOX"; reason = "No exported executable was launched." }

if ($ExportPreset) {
    if (-not $ExportPath) {
        $exportDir = Join-Path $runDir "export"
        New-Item -ItemType Directory -Path $exportDir | Out-Null
        $ExportPath = Join-Path $exportDir $(if ($IsWindows) { "game.exe" } else { "game" })
    } elseif (-not [IO.Path]::IsPathRooted($ExportPath)) { $ExportPath = Join-Path $resolvedProject $ExportPath }
    $exportParent = Split-Path -Parent $ExportPath
    if (-not (Test-Path -LiteralPath $exportParent)) { New-Item -ItemType Directory -Path $exportParent | Out-Null }
    $checks.export_build = Invoke-CapturedProcess -FilePath $resolvedGodot -Arguments @("--headless", "--path", $resolvedProject, "--export-debug", $ExportPreset, $ExportPath) -Timeout ([Math]::Max($TimeoutSeconds, 120)) -LogPath (Join-Path $runDir "export-build.log")
    if ($checks.export_build.status -eq "pass" -and (Test-Path -LiteralPath $ExportPath -PathType Leaf)) {
        $extension = [IO.Path]::GetExtension($ExportPath)
        if (($IsWindows -and $extension -ieq ".exe") -or (-not $IsWindows -and -not $extension)) {
            $checks.export_black_box = Invoke-CapturedProcess -FilePath $ExportPath -Arguments @("--headless", "--quit-after", "120") -Timeout $TimeoutSeconds -LogPath (Join-Path $runDir "export-black-box.log")
            $checks.export_black_box.level = "L4"
            $checks.export_black_box.label = "EXPORTED_BLACK_BOX"
        } else { $checks.export_black_box.reason = "Export artifact is not directly executable on this host: $ExportPath" }
    }
}

$attemptedFailures = @($checks.GetEnumerator() | Where-Object { $_.Value.status -eq "fail" })
$highest = if ($checks.export_black_box.status -eq "pass") { [ordered]@{ level = "L4"; label = "EXPORTED_BLACK_BOX" } } elseif ($checks.headless_runtime.status -eq "pass" -and $checks.project_import.status -eq "pass") { [ordered]@{ level = "L1"; label = "HEADLESS_SMOKE" } } else { [ordered]@{ level = "L0"; label = "SOURCE_INSPECTED" } }
$receipt = [ordered]@{
    schema = "godot-game-validation.v1"
    run_id = $runId
    started_at_utc = [DateTime]::UtcNow.ToString("o")
    project_path = $resolvedProject
    scene = if ($Scene) { $Scene } else { "project main scene" }
    godot_path = $resolvedGodot
    godot_version = $godotVersion
    git = [ordered]@{ commit = $gitCommit; dirty = $gitDirty }
    checks = $checks
    highest_evidence = $highest
    overall_status = if ($attemptedFailures.Count -eq 0) { "pass" } else { "fail" }
    artifact_directory = $runDir
}
$receiptPath = Join-Path $runDir "receipt.json"
[IO.File]::WriteAllText($receiptPath, ($receipt | ConvertTo-Json -Depth 12), $script:Utf8NoBom)
Write-Host "Validation receipt: $receiptPath"
Write-Host "Highest evidence: $($highest.level) $($highest.label)"
Write-Host "Overall status: $($receipt.overall_status)"
if ($attemptedFailures.Count -gt 0) { exit 1 }
