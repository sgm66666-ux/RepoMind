param(
    [ValidateSet('inventory', 'register', 'price')][string]$Demo = 'inventory',
    [switch]$SkipAnalysis,
    [string]$PythonExe,
    [string]$PythonSitePackages,
    [string]$MavenExe,
    [string]$JavaHome,
    [string]$NpmExe,
    [string]$OllamaUrl = 'http://127.0.0.1:11434'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Probe([string]$url) {
    try { return Invoke-RestMethod -Uri $url -TimeoutSec 2 }
    catch { return $null }
}
function PortOwner([int]$port) {
    try {
        $owner = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop | Select-Object -First 1 -ExpandProperty OwningProcess
        if ($owner) { return [string]$owner }
    } catch { }
    $line = netstat -ano -p TCP | Where-Object { $_ -match "\s(?:127\.0\.0\.1|0\.0\.0\.0|\[::\]):$port\s+.*LISTENING\s+(\d+)\s*$" } | Select-Object -First 1
    if ($line -match 'LISTENING\s+(\d+)\s*$') { return $Matches[1] }
    return 'unknown'
}
function StartOrVerify([string]$name, [int]$port, [string]$url, [string]$executable,
                       [string[]]$arguments, [string]$workingDirectory, [int]$waitSeconds) {
    if (Probe $url) { Write-Host "$name already reachable at $url"; return }
    $owner = PortOwner $port
    if ($owner -ne 'unknown') { throw "$name cannot start: port $port is occupied by PID $owner, but $url is not healthy." }
    $logs = Join-Path $root 'logs'
    New-Item -ItemType Directory -Path $logs -Force | Out-Null
    $stem = ($name -replace '[^A-Za-z0-9]', '-').ToLowerInvariant() + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
    $stdout = Join-Path $logs "$stem.out.log"
    $stderr = Join-Path $logs "$stem.err.log"
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $workingDirectory -WindowStyle Hidden -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    for ($elapsed = 0; $elapsed -lt $waitSeconds; $elapsed++) {
        Start-Sleep -Seconds 1
        if (Probe $url) { Write-Host "$name ready at $url (started PID $($process.Id))"; return }
        if ($process.HasExited) {
            $tail = if (Test-Path $stderr) { (Get-Content -LiteralPath $stderr -Tail 12) -join "`n" } else { '' }
            throw "$name exited during startup (PID $($process.Id), code $($process.ExitCode)); stderr: $stderr`n$tail"
        }
    }
    throw "$name did not become ready at $url within $waitSeconds seconds; started PID $($process.Id). Logs: $stdout, $stderr"
}

$tags = Probe "$($OllamaUrl.TrimEnd('/'))/api/tags"
if (-not $tags) { throw "Ollama is not reachable at $OllamaUrl. Start the installed Ollama service first; no model will be downloaded." }
if (-not @($tags.models | Where-Object name -eq 'qwen2.5-coder:14b').Count) {
    throw 'Required local model qwen2.5-coder:14b is absent. Install it explicitly before starting the demo.'
}

if (-not $PythonExe) {
    $candidate = Join-Path $root 'services/python-service/.venv/Scripts/python.exe'
    if (Test-Path $candidate) { $PythonExe = $candidate }
    else {
        $command = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($command) { $PythonExe = $command.Source }
    }
}
if (-not $PythonExe -or -not (Test-Path $PythonExe)) { throw 'Python executable not found. Create the documented venv or pass -PythonExe.' }
if ($PythonSitePackages) {
    if (-not (Test-Path $PythonSitePackages)) { throw "Python site-packages not found: $PythonSitePackages" }
    $env:PYTHONPATH = $PythonSitePackages + [IO.Path]::PathSeparator + $env:PYTHONPATH
}
& $PythonExe -c 'import fastapi, uvicorn, tree_sitter' 2>$null
if ($LASTEXITCODE -ne 0) { throw "Python dependencies missing or interpreter broken: $PythonExe. Recreate the venv and install requirements.txt." }

if ($JavaHome) {
    if (-not (Test-Path (Join-Path $JavaHome 'bin/java.exe'))) { throw "Invalid JavaHome: $JavaHome" }
    $env:JAVA_HOME = $JavaHome
    $env:PATH = (Join-Path $JavaHome 'bin') + [IO.Path]::PathSeparator + $env:PATH
}
if (-not $MavenExe) {
    $command = Get-Command mvn.cmd -ErrorAction SilentlyContinue
    if ($command) { $MavenExe = $command.Source }
}
if (-not $MavenExe -or -not (Test-Path $MavenExe)) { throw 'Maven not found. Install Maven or pass -MavenExe.' }
if (-not $NpmExe) {
    $command = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($command) { $NpmExe = $command.Source }
}
if (-not $NpmExe -or -not (Test-Path $NpmExe)) { throw 'npm not found. Install Node.js or pass -NpmExe.' }
if (-not (Test-Path (Join-Path $root 'services/frontend/node_modules'))) {
    throw 'Frontend dependencies are absent. Run npm ci in services/frontend first.'
}

$env:REPOMIND_LLM_PROVIDER = 'ollama'
$env:OLLAMA_BASE_URL = $OllamaUrl
$env:OLLAMA_MODEL = 'qwen2.5-coder:14b'
$env:OLLAMA_REQUEST_TIMEOUT_SECONDS = '180'
$env:REPOMIND_PYTHON_SERVICE_URL = 'http://127.0.0.1:8000'

StartOrVerify 'Python API' 8000 'http://127.0.0.1:8000/health' $PythonExe @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') (Join-Path $root 'services/python-service') 45
StartOrVerify 'Spring Boot gateway' 8080 'http://127.0.0.1:8080/api/health' $MavenExe @('spring-boot:run','-q') (Join-Path $root 'services/java-service') 120
StartOrVerify 'Vue frontend' 5173 'http://127.0.0.1:5173' $NpmExe @('run','dev','--','--host','127.0.0.1') (Join-Path $root 'services/frontend') 45

if (-not $SkipAnalysis) {
    & (Join-Path $PSScriptRoot 'prepare-demo.ps1') -Demo $Demo -PythonUrl 'http://127.0.0.1:8000' | Out-Null
}
& (Join-Path $PSScriptRoot 'check-readiness.ps1') -OllamaUrl $OllamaUrl -Demo $Demo -RequireAnalysis:(-not $SkipAnalysis) -Strict
Write-Host 'Frontend: http://127.0.0.1:5173'
Write-Host 'Gateway:  http://127.0.0.1:8080/api/health'
Write-Host 'Python:   http://127.0.0.1:8000/health'
Write-Host 'API docs: http://127.0.0.1:8000/docs'
