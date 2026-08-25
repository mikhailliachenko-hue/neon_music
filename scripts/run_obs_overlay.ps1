param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectDir,
    [Parameter(Mandatory = $true)]
    [string]$GodotPath
)

$ErrorActionPreference = "Stop"
$resolvedProject = (Resolve-Path -LiteralPath $ProjectDir).ProviderPath
$overridePath = Join-Path $resolvedProject "override.cfg"
$backupPath = Join-Path ([IO.Path]::GetTempPath()) ("neon-music-override-{0}.cfg" -f [guid]::NewGuid().ToString("N"))
$hadOverride = Test-Path -LiteralPath $overridePath -PathType Leaf

try {
    if ($hadOverride) {
        Copy-Item -LiteralPath $overridePath -Destination $backupPath
    }
    $overrideText = @"
[display]

window/per_pixel_transparency/allowed=true
"@
    [IO.File]::WriteAllText($overridePath, $overrideText, [Text.UTF8Encoding]::new($false))
    $godotArguments = @(
        "--path",
        $resolvedProject,
        "--resolution",
        "2560x1440",
        "--",
        "--obs-overlay",
        "--render-clock=audio",
        "--no-tuning-gui"
    )
    # Windows PowerShell 5 does not expose ProcessStartInfo.ArgumentList.
    # Start-Process keeps this wrapper alive until Godot closes, so the
    # process-scoped override cannot disappear during an OBS capture.
    $godotProcess = Start-Process -FilePath $GodotPath -ArgumentList $godotArguments -PassThru -Wait
    $exitCode = $godotProcess.ExitCode
}
finally {
    if ($hadOverride -and (Test-Path -LiteralPath $backupPath -PathType Leaf)) {
        Copy-Item -LiteralPath $backupPath -Destination $overridePath -Force
        Remove-Item -LiteralPath $backupPath -Force
    }
    elseif (Test-Path -LiteralPath $overridePath -PathType Leaf) {
        Remove-Item -LiteralPath $overridePath -Force
    }
}

exit $exitCode
