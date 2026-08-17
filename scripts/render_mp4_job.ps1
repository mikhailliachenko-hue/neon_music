param(
    [Parameter(Mandatory = $true)]
    [string]$RequestPath
)

$ErrorActionPreference = "Stop"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$request = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json

function Write-JobStatus {
    param(
        [string]$State,
        [string]$Message,
        [string]$Encoder = ""
    )
    $payload = [ordered]@{
        state = $State
        message = $Message
        output = [string]$request.mp4
        encoder = $Encoder
        updated_at = [DateTimeOffset]::Now.ToString("o")
    } | ConvertTo-Json
    [System.IO.File]::WriteAllText([string]$request.status, $payload, $utf8NoBom)
}

function Test-RenderedAvi {
    param(
        [string]$Path,
        [double]$ExpectedDuration,
        [int]$ExpectedFps
    )
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf) -or (Get-Item -LiteralPath $Path).Length -le 0) {
        return $false
    }
    $ffprobe = Join-Path (Split-Path -Parent ([string]$request.ffmpeg)) "ffprobe.exe"
    if (-not (Test-Path -LiteralPath $ffprobe -PathType Leaf)) {
        return $false
    }
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    $probeText = (& $ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames -of json $Path 2>$null | Out-String)
    $ErrorActionPreference = $previousPreference
    try {
        $probe = $probeText | ConvertFrom-Json
        $frames = [int]$probe.streams[0].nb_read_frames
        $minimumFrames = [Math]::Max(1, [Math]::Floor($ExpectedDuration * $ExpectedFps) - 1)
        return $frames -ge $minimumFrames
    }
    catch {
        return $false
    }
}

try {
    foreach ($required in @($request.godot, $request.ffmpeg, $request.audio)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Required file is missing: $required"
        }
    }

    $duration = [double]$request.duration
    $fps = [int]$request.fps
    $godotArgs = @(
        "--rendering-driver", "vulkan",
        "--path", [string]$request.project,
        "--write-movie", [string]$request.avi,
        "--fixed-fps", [string]$fps,
        "--resolution", [string]$request.resolution,
        "--"
    )
    $godotArgs += @($request.user_args | ForEach-Object { [string]$_ })
    $godotArgs += @(
        "--audio=$($request.audio)",
        "--render-clock=frame",
        "--clock-fps=$fps",
        "--clock-start-at=0",
        "--clock-stop-after=$($duration.ToString('0.000000', [Globalization.CultureInfo]::InvariantCulture))",
        "--no-tuning-gui"
    )

    Write-JobStatus -State "rendering" -Message "Rendering frames from 0:00..."
    $renderComplete = $false
    $godotExitCode = 0
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        Remove-Item -LiteralPath ([string]$request.avi) -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath ([string]$request.mp4) -Force -ErrorAction SilentlyContinue
        $ErrorActionPreference = "Continue"
        & ([string]$request.godot) @godotArgs *> ([string]$request.log)
        $godotExitCode = $LASTEXITCODE
        $ErrorActionPreference = "Stop"
        if (Test-RenderedAvi -Path ([string]$request.avi) -ExpectedDuration $duration -ExpectedFps $fps) {
            $renderComplete = $true
            break
        }
        Add-Content -LiteralPath ([string]$request.log) -Value "Incomplete Movie Writer output on attempt $attempt (exit $godotExitCode)."
        Start-Sleep -Milliseconds 750
    }
    if (-not $renderComplete) {
        throw "Godot Movie Writer did not produce the complete frame range. Log: $($request.log)"
    }
    if ($godotExitCode -ne 0) {
        Add-Content -LiteralPath ([string]$request.log) -Value "Godot returned $godotExitCode after producing a complete AVI; continuing with validated output."
    }

    Write-JobStatus -State "encoding" -Message "Encoding the final MP4 on the GPU..." -Encoder "h264_nvenc"
    $durationText = $duration.ToString("0.000000", [Globalization.CultureInfo]::InvariantCulture)
    $resolutionParts = ([string]$request.resolution).Split("x")
    if ($resolutionParts.Count -ne 2) {
        throw "Invalid output resolution: $($request.resolution)"
    }
    $scaleFilter = "scale=$($resolutionParts[0]):$($resolutionParts[1]):flags=lanczos"
    $common = @(
        "-y",
        "-i", [string]$request.avi,
        "-i", [string]$request.audio,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-t", $durationText,
        "-vf", $scaleFilter,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "320k",
        "-movflags", "+faststart"
    )
    $nvencArgs = $common + @("-c:v", "h264_nvenc", "-preset", "p5", "-cq", "18", [string]$request.mp4)
    $ErrorActionPreference = "Continue"
    & ([string]$request.ffmpeg) @nvencArgs >> ([string]$request.log) 2>&1
    $encodeExitCode = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    $encoder = "h264_nvenc"

    if ($encodeExitCode -ne 0) {
        Write-JobStatus -State "encoding" -Message "GPU encoding is unavailable; continuing on the CPU..." -Encoder "libx264"
        $cpuArgs = $common + @("-c:v", "libx264", "-preset", "medium", "-crf", "18", [string]$request.mp4)
        $ErrorActionPreference = "Continue"
        & ([string]$request.ffmpeg) @cpuArgs >> ([string]$request.log) 2>&1
        $encodeExitCode = $LASTEXITCODE
        $ErrorActionPreference = "Stop"
        $encoder = "libx264"
    }

    if ($encodeExitCode -ne 0 -or -not (Test-Path -LiteralPath $request.mp4 -PathType Leaf)) {
        throw "FFmpeg MP4 encoding failed with exit code $encodeExitCode. Log: $($request.log)"
    }

    Remove-Item -LiteralPath $request.avi -Force -ErrorAction SilentlyContinue
    Write-JobStatus -State "complete" -Message "Done: MP4 created; opening the output folder" -Encoder $encoder
    exit 0
}
catch {
    Write-JobStatus -State "error" -Message ("Render error: " + $_.Exception.Message)
    exit 1
}
