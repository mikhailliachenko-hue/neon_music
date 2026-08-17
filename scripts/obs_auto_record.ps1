param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Prepare', 'Start', 'Stop')]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$StatusPath,

    [Parameter(Mandatory = $true)]
    [string]$StatePath,

    [string]$SceneName = 'Neon Auto Recording',

    [string]$BackgroundPath = '',

    [string]$AudioPath = '',

    [string]$GameWindow = 'Neon Footstep Renderer (DEBUG):Engine:Godot_v4.7.1-stable_win64.exe'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$recordedOutputPath = ''

function Write-JsonFile {
    param([string]$Path, [hashtable]$Value)
    $directory = Split-Path -Parent $Path
    if ($directory -and -not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Force -Path $directory | Out-Null
    }
    $json = $Value | ConvertTo-Json -Depth 12 -Compress
    [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
}

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { throw "OBS state file not found: $Path" }
    return [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
}

function Write-Status {
    param([string]$State, [string]$Message, [string]$OutputPath = '')
    Write-JsonFile -Path $StatusPath -Value @{
        state = $State
        message = $Message
        output_path = $OutputPath
        updated_utc = [DateTime]::UtcNow.ToString('o')
    }
}

function Read-ObsConfig {
    $configPath = Join-Path $env:APPDATA 'obs-studio\plugin_config\obs-websocket\config.json'
    if (-not (Test-Path -LiteralPath $configPath)) {
        throw "OBS WebSocket config not found: $configPath"
    }
    $config = Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json
    if (-not [bool]$config.server_enabled) {
        throw 'OBS WebSocket is disabled. Enable Tools > WebSocket Server Settings > Enable WebSocket server once.'
    }
    return $config
}

function Find-ObsExecutable {
    $candidates = @(
        'C:\Program Files\obs-studio\bin\64bit\obs64.exe',
        'C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe'
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    throw 'OBS Studio executable was not found.'
}

function Start-ObsIfNeeded {
    if (Get-Process -Name 'obs64' -ErrorAction SilentlyContinue) { return }
    $obsPath = Find-ObsExecutable
    Start-Process -FilePath $obsPath -ArgumentList '--minimize-to-tray' -WindowStyle Hidden | Out-Null
}

function Send-WebSocketJson {
    param([System.Net.WebSockets.ClientWebSocket]$Socket, [hashtable]$Payload)
    $json = $Payload | ConvertTo-Json -Depth 20 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $segment = [ArraySegment[byte]]::new($bytes)
    $Socket.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
}

function Receive-WebSocketJson {
    param([System.Net.WebSockets.ClientWebSocket]$Socket)
    $buffer = New-Object byte[] 65536
    $stream = [System.IO.MemoryStream]::new()
    try {
        do {
            $segment = [ArraySegment[byte]]::new($buffer)
            $result = $Socket.ReceiveAsync($segment, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
            if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
                throw "OBS WebSocket closed: $($result.CloseStatusDescription)"
            }
            $stream.Write($buffer, 0, $result.Count)
        } while (-not $result.EndOfMessage)
        $json = [System.Text.Encoding]::UTF8.GetString($stream.ToArray())
        return $json | ConvertFrom-Json
    }
    finally {
        $stream.Dispose()
    }
}

function Get-ObsAuthentication {
    param([string]$Password, [string]$Salt, [string]$Challenge)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $secretBytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Password + $Salt))
        $secret = [Convert]::ToBase64String($secretBytes)
        $authBytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($secret + $Challenge))
        return [Convert]::ToBase64String($authBytes)
    }
    finally {
        $sha.Dispose()
    }
}

function Connect-Obs {
    param($Config)
    $lastError = $null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $socket = [System.Net.WebSockets.ClientWebSocket]::new()
        $socket.Options.AddSubProtocol('obswebsocket.json')
        try {
            $uri = [Uri]("ws://127.0.0.1:{0}" -f [int]$Config.server_port)
            $socket.ConnectAsync($uri, [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
            $hello = Receive-WebSocketJson -Socket $socket
            if ([int]$hello.op -ne 0) { throw 'OBS did not send a Hello message.' }
            $identifyData = @{ rpcVersion = 1; eventSubscriptions = 0 }
            if ($hello.d.authentication) {
                $identifyData.authentication = Get-ObsAuthentication -Password ([string]$Config.server_password) -Salt ([string]$hello.d.authentication.salt) -Challenge ([string]$hello.d.authentication.challenge)
            }
            Send-WebSocketJson -Socket $socket -Payload @{ op = 1; d = $identifyData }
            $identified = Receive-WebSocketJson -Socket $socket
            if ([int]$identified.op -ne 2) { throw 'OBS WebSocket authentication failed.' }
            return $socket
        }
        catch {
            $lastError = $_
            $socket.Dispose()
            Start-Sleep -Milliseconds 250
        }
    }
    throw "Could not connect to OBS WebSocket: $lastError"
}

function Invoke-ObsRequest {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [string]$RequestType,
        [hashtable]$RequestData = @{}
    )
    $requestId = [Guid]::NewGuid().ToString('N')
    Send-WebSocketJson -Socket $Socket -Payload @{
        op = 6
        d = @{
            requestType = $RequestType
            requestId = $requestId
            requestData = $RequestData
        }
    }
    while ($true) {
        $message = Receive-WebSocketJson -Socket $Socket
        if ([int]$message.op -ne 7 -or [string]$message.d.requestId -ne $requestId) { continue }
        if (-not [bool]$message.d.requestStatus.result) {
            throw "OBS request $RequestType failed: $($message.d.requestStatus.comment)"
        }
        if ($message.d.PSObject.Properties.Name -contains 'responseData') {
            return $message.d.responseData
        }
        return @{}
    }
}

function Ensure-CaptureScene {
    param(
        [System.Net.WebSockets.ClientWebSocket]$Socket,
        [string]$TargetScene,
        [string]$VideoPath,
        [string]$MusicPath,
        [string]$WindowMatch
    )
    if (-not (Test-Path -LiteralPath $VideoPath)) { throw "Background MP4 not found: $VideoPath" }
    if (-not (Test-Path -LiteralPath $MusicPath)) { throw "Track audio not found: $MusicPath" }
    $sceneList = Invoke-ObsRequest -Socket $Socket -RequestType 'GetSceneList'
    $sceneExists = @($sceneList.scenes | Where-Object { [string]$_.sceneName -eq $TargetScene }).Count -gt 0
    if (-not $sceneExists) {
        Invoke-ObsRequest -Socket $Socket -RequestType 'CreateScene' -RequestData @{ sceneName = $TargetScene } | Out-Null
    }

    $backgroundInput = 'Neon Auto Background'
    $inputs = (Invoke-ObsRequest -Socket $Socket -RequestType 'GetInputList').inputs
    $backgroundExists = @($inputs | Where-Object { [string]$_.inputName -eq $backgroundInput }).Count -gt 0
    $backgroundSettings = @{
        is_local_file = $true
        local_file = $VideoPath
        looping = $true
        restart_on_activate = $false
        close_when_inactive = $false
        hw_decode = $true
        clear_on_media_end = $false
    }

    $audioInput = 'Neon Auto Music'
    $inputs = (Invoke-ObsRequest -Socket $Socket -RequestType 'GetInputList').inputs
    $audioExists = @($inputs | Where-Object { [string]$_.inputName -eq $audioInput }).Count -gt 0
    $audioSettings = @{
        is_local_file = $true
        local_file = $MusicPath
        looping = $false
        restart_on_activate = $false
        close_when_inactive = $false
        clear_on_media_end = $false
    }
    if (-not $audioExists) {
        Invoke-ObsRequest -Socket $Socket -RequestType 'CreateInput' -RequestData @{
            sceneName = $TargetScene
            inputName = $audioInput
            inputKind = 'ffmpeg_source'
            inputSettings = $audioSettings
            sceneItemEnabled = $true
        } | Out-Null
    }
    else {
        Invoke-ObsRequest -Socket $Socket -RequestType 'SetInputSettings' -RequestData @{ inputName = $audioInput; inputSettings = $audioSettings; overlay = $false } | Out-Null
        try {
            Invoke-ObsRequest -Socket $Socket -RequestType 'GetSceneItemId' -RequestData @{ sceneName = $TargetScene; sourceName = $audioInput } | Out-Null
        }
        catch {
            Invoke-ObsRequest -Socket $Socket -RequestType 'CreateSceneItem' -RequestData @{ sceneName = $TargetScene; sourceName = $audioInput; sceneItemEnabled = $true } | Out-Null
        }
    }
    if (-not $backgroundExists) {
        $created = Invoke-ObsRequest -Socket $Socket -RequestType 'CreateInput' -RequestData @{
            sceneName = $TargetScene
            inputName = $backgroundInput
            inputKind = 'ffmpeg_source'
            inputSettings = $backgroundSettings
            sceneItemEnabled = $true
        }
        $backgroundItemId = [int]$created.sceneItemId
    }
    else {
        Invoke-ObsRequest -Socket $Socket -RequestType 'SetInputSettings' -RequestData @{ inputName = $backgroundInput; inputSettings = $backgroundSettings; overlay = $false } | Out-Null
        try {
            $item = Invoke-ObsRequest -Socket $Socket -RequestType 'GetSceneItemId' -RequestData @{ sceneName = $TargetScene; sourceName = $backgroundInput }
            $backgroundItemId = [int]$item.sceneItemId
        }
        catch {
            $createdItem = Invoke-ObsRequest -Socket $Socket -RequestType 'CreateSceneItem' -RequestData @{ sceneName = $TargetScene; sourceName = $backgroundInput; sceneItemEnabled = $true }
            $backgroundItemId = [int]$createdItem.sceneItemId
        }
    }

    $gameInput = 'Neon Auto Game'
    $gameExists = @($inputs | Where-Object { [string]$_.inputName -eq $gameInput }).Count -gt 0
    $gameSettings = @{ capture_audio = $false; window = $WindowMatch; method = 2; cursor = $false }
    if (-not $gameExists) {
        $createdGame = Invoke-ObsRequest -Socket $Socket -RequestType 'CreateInput' -RequestData @{
            sceneName = $TargetScene
            inputName = $gameInput
            inputKind = 'window_capture'
            inputSettings = $gameSettings
            sceneItemEnabled = $true
        }
        $gameItemId = [int]$createdGame.sceneItemId
    }
    else {
        Invoke-ObsRequest -Socket $Socket -RequestType 'SetInputSettings' -RequestData @{ inputName = $gameInput; inputSettings = $gameSettings; overlay = $false } | Out-Null
        try {
            $gameItem = Invoke-ObsRequest -Socket $Socket -RequestType 'GetSceneItemId' -RequestData @{ sceneName = $TargetScene; sourceName = $gameInput }
            $gameItemId = [int]$gameItem.sceneItemId
        }
        catch {
            $createdGameItem = Invoke-ObsRequest -Socket $Socket -RequestType 'CreateSceneItem' -RequestData @{ sceneName = $TargetScene; sourceName = $gameInput; sceneItemEnabled = $true }
            $gameItemId = [int]$createdGameItem.sceneItemId
        }
    }

    $video = Invoke-ObsRequest -Socket $Socket -RequestType 'GetVideoSettings'
    foreach ($sceneItemId in @($backgroundItemId, $gameItemId)) {
        Invoke-ObsRequest -Socket $Socket -RequestType 'SetSceneItemTransform' -RequestData @{
            sceneName = $TargetScene
            sceneItemId = $sceneItemId
            sceneItemTransform = @{
                positionX = 0.0
                positionY = 0.0
                rotation = 0.0
                boundsType = 'OBS_BOUNDS_STRETCH'
                boundsAlignment = 5
                boundsWidth = [double]$video.baseWidth
                boundsHeight = [double]$video.baseHeight
            }
        } | Out-Null
        Invoke-ObsRequest -Socket $Socket -RequestType 'SetSceneItemEnabled' -RequestData @{ sceneName = $TargetScene; sceneItemId = $sceneItemId; sceneItemEnabled = $true } | Out-Null
    }
    Invoke-ObsRequest -Socket $Socket -RequestType 'SetSceneItemIndex' -RequestData @{ sceneName = $TargetScene; sceneItemId = $backgroundItemId; sceneItemIndex = 0 } | Out-Null
    Invoke-ObsRequest -Socket $Socket -RequestType 'SetSceneItemIndex' -RequestData @{ sceneName = $TargetScene; sceneItemId = $gameItemId; sceneItemIndex = 1 } | Out-Null
    # The looping visual MP4 is deliberately silent. The complete source WAV is
    # restarted alongside it, so a short background loop cannot cut off music.
    Invoke-ObsRequest -Socket $Socket -RequestType 'SetInputMute' -RequestData @{ inputName = $backgroundInput; inputMuted = $true } | Out-Null
    Invoke-ObsRequest -Socket $Socket -RequestType 'SetInputMute' -RequestData @{ inputName = $audioInput; inputMuted = $false } | Out-Null
    Invoke-ObsRequest -Socket $Socket -RequestType 'SetInputAudioMonitorType' -RequestData @{
        inputName = $backgroundInput
        monitorType = 'OBS_MONITORING_TYPE_NONE'
    } | Out-Null
    Invoke-ObsRequest -Socket $Socket -RequestType 'SetInputAudioMonitorType' -RequestData @{
        inputName = $audioInput
        monitorType = 'OBS_MONITORING_TYPE_NONE'
    } | Out-Null
    return @{
        background_input = $backgroundInput
        audio_input = $audioInput
        game_input = $gameInput
    }
}

function Protect-DesktopAudio {
    param([System.Net.WebSockets.ClientWebSocket]$Socket)
    $protected = @()
    $deviceKinds = @('wasapi_output_capture', 'wasapi_input_capture', 'wasapi_process_output_capture')
    foreach ($input in (Invoke-ObsRequest -Socket $Socket -RequestType 'GetInputList').inputs) {
        if ($deviceKinds -notcontains [string]$input.inputKind) { continue }
        $name = [string]$input.inputName
        $mute = Invoke-ObsRequest -Socket $Socket -RequestType 'GetInputMute' -RequestData @{ inputName = $name }
        $protected += @{ input_name = $name; was_muted = [bool]$mute.inputMuted }
        Invoke-ObsRequest -Socket $Socket -RequestType 'SetInputMute' -RequestData @{ inputName = $name; inputMuted = $true } | Out-Null
    }
    return @($protected)
}

function Restore-DesktopAudio {
    param([System.Net.WebSockets.ClientWebSocket]$Socket, $ProtectedInputs)
    foreach ($input in @($ProtectedInputs)) {
        if ($null -eq $input) { continue }
        Invoke-ObsRequest -Socket $Socket -RequestType 'SetInputMute' -RequestData @{
            inputName = [string]$input.input_name
            inputMuted = [bool]$input.was_muted
        } | Out-Null
    }
}

Write-Status -State 'working' -Message "OBS automation: $Action"
$requestedAction = ([string]$Action).Trim().ToLowerInvariant()
$socket = $null
try {
    $config = Read-ObsConfig
    Start-ObsIfNeeded
    $socket = Connect-Obs -Config $config
    if ($requestedAction -eq 'prepare') {
        $recordStatus = Invoke-ObsRequest -Socket $socket -RequestType 'GetRecordStatus'
        if ([bool]$recordStatus.outputActive) { throw 'OBS is already recording. Stop the current recording first.' }
        $currentScene = (Invoke-ObsRequest -Socket $socket -RequestType 'GetCurrentProgramScene').currentProgramSceneName
        $capture = Ensure-CaptureScene -Socket $socket -TargetScene $SceneName -VideoPath $BackgroundPath -MusicPath $AudioPath -WindowMatch $GameWindow
        $protectedInputs = Protect-DesktopAudio -Socket $socket
        Invoke-ObsRequest -Socket $socket -RequestType 'SetCurrentProgramScene' -RequestData @{ sceneName = $SceneName } | Out-Null
        Invoke-ObsRequest -Socket $socket -RequestType 'TriggerMediaInputAction' -RequestData @{ inputName = [string]$capture.background_input; mediaAction = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_STOP' } | Out-Null
        Invoke-ObsRequest -Socket $socket -RequestType 'TriggerMediaInputAction' -RequestData @{ inputName = [string]$capture.audio_input; mediaAction = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_STOP' } | Out-Null
        Write-JsonFile -Path $StatePath -Value @{
            scene_name = $SceneName
            previous_scene = [string]$currentScene
            background_input = [string]$capture.background_input
            audio_input = [string]$capture.audio_input
            game_input = [string]$capture.game_input
            protected_inputs = @($protectedInputs)
        }
        Write-Status -State 'ready' -Message 'OBS is ready. Recording starts after countdown.'
    }
    if ($requestedAction -eq 'start') {
        $state = Read-JsonFile -Path $StatePath
        Invoke-ObsRequest -Socket $socket -RequestType 'SetCurrentProgramScene' -RequestData @{ sceneName = [string]$state.scene_name } | Out-Null
        $recordStatus = Invoke-ObsRequest -Socket $socket -RequestType 'GetRecordStatus'
        if ([bool]$recordStatus.outputActive) { throw 'OBS is already recording.' }
        Invoke-ObsRequest -Socket $socket -RequestType 'StartRecord' | Out-Null
        Invoke-ObsRequest -Socket $socket -RequestType 'TriggerMediaInputAction' -RequestData @{ inputName = [string]$state.background_input; mediaAction = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART' } | Out-Null
        Invoke-ObsRequest -Socket $socket -RequestType 'TriggerMediaInputAction' -RequestData @{ inputName = [string]$state.audio_input; mediaAction = 'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART' } | Out-Null
        Write-Status -State 'recording' -Message 'OBS is recording from 0:00.'
    }
    if ($requestedAction -eq 'stop') {
        $state = Read-JsonFile -Path $StatePath
        $recordStatus = Invoke-ObsRequest -Socket $socket -RequestType 'GetRecordStatus'
        Write-Status -State 'finalizing' -Message 'OBS is finalizing MP4...'
        $recordedOutputPath = ''
        if ($null -ne $recordStatus -and $recordStatus.PSObject.Properties.Name -contains 'outputPath') {
            $recordedOutputPath = [string]$recordStatus.outputPath
        }
        if ([bool]$recordStatus.outputActive) {
            $stopped = Invoke-ObsRequest -Socket $socket -RequestType 'StopRecord'
            if ($null -ne $stopped -and $stopped.PSObject.Properties.Name -contains 'outputPath') {
                $recordedOutputPath = [string]$stopped.outputPath
            }
        }
        if (-not $recordedOutputPath) {
            $profile = Invoke-ObsRequest -Socket $socket -RequestType 'GetProfileParameter' -RequestData @{ parameterCategory = 'SimpleOutput'; parameterName = 'FilePath' }
            $recordDirectory = [string]$profile.parameterValue
            if (Test-Path -LiteralPath $recordDirectory) {
                $latestMp4 = Get-ChildItem -LiteralPath $recordDirectory -Filter '*.mp4' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
                if ($null -ne $latestMp4) { $recordedOutputPath = $latestMp4.FullName }
            }
        }
        if ($recordedOutputPath) {
            $stableChecks = 0
            $lastLength = -1L
            for ($attempt = 0; $attempt -lt 80; $attempt++) {
                if (Test-Path -LiteralPath $recordedOutputPath) {
                    $currentLength = (Get-Item -LiteralPath $recordedOutputPath).Length
                    if ($currentLength -gt 0 -and $currentLength -eq $lastLength) {
                        $stableChecks++
                        if ($stableChecks -ge 3) { break }
                    }
                    else {
                        $stableChecks = 0
                    }
                    $lastLength = $currentLength
                }
                Start-Sleep -Milliseconds 250
            }
        }
        if ([string]$state.previous_scene) {
            Invoke-ObsRequest -Socket $socket -RequestType 'SetCurrentProgramScene' -RequestData @{ sceneName = [string]$state.previous_scene } | Out-Null
        }
        Restore-DesktopAudio -Socket $socket -ProtectedInputs $state.protected_inputs
        Write-Status -State 'complete' -Message 'Recording is complete.' -OutputPath $recordedOutputPath
    }
}
catch {
    Write-Status -State 'error' -Message $_.Exception.Message
    exit 1
}
finally {
    if ($null -ne $socket) { $socket.Dispose() }
}
