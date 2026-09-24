param(
    [string]$OllamaUrl = 'http://127.0.0.1:11434',
    [string]$PythonUrl = 'http://127.0.0.1:8000',
    [string]$JavaUrl = 'http://127.0.0.1:8080',
    [string]$FrontendUrl = 'http://127.0.0.1:5173',
    [string]$Model = 'qwen2.5-coder:14b',
    [ValidateSet('inventory', 'register', 'price')][string]$Demo = 'inventory',
    [switch]$RequireAnalysis,
    [switch]$Strict
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$relative = @{
    inventory = 'demo/order-demo'
    register = 'demo/repomind-agent-test-demo/call-chain-demo'
    price = 'demo/repomind-agent-test-demo/logic-bug-demo'
}
$expected = (Resolve-Path (Join-Path $root $relative[$Demo])).Path

function Probe([string]$url) {
    try { return Invoke-RestMethod -Uri $url -TimeoutSec 3 }
    catch { return $null }
}

$ollama = Probe "$($OllamaUrl.TrimEnd('/'))/api/tags"
$python = Probe "$($PythonUrl.TrimEnd('/'))/health"
$java = Probe "$($JavaUrl.TrimEnd('/'))/api/health"
$frontend = $false
try { $frontend = (Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 }
catch { $frontend = $false }
$analysis = if ($python) { Probe "$($PythonUrl.TrimEnd('/'))/analysis/status" } else { $null }
$modelAvailable = [bool]($ollama -and @($ollama.models | Where-Object name -eq $Model).Count -gt 0)
$indexReady = [bool]($analysis -and $analysis.analysisReady -eq $true -and $analysis.repositoryPath -and
    [IO.Path]::GetFullPath($analysis.repositoryPath) -eq [IO.Path]::GetFullPath($expected))
$result = [pscustomobject]@{
    ollamaReachable = [bool]$ollama
    requiredModelAvailable = $modelAvailable
    pythonApiReachable = [bool]($python -and $python.status -eq 'ok')
    javaApiReachable = [bool]($java -and $java.status -eq 'ok')
    frontendReachable = $frontend
    demoIndexReady = $indexReady
    analyzedRepository = if ($analysis) { $analysis.repositoryPath } else { $null }
    expectedRepository = $expected
}
Write-Output $result
if ($Strict -and (-not $result.ollamaReachable -or -not $result.requiredModelAvailable -or
                -not $result.pythonApiReachable -or -not $result.javaApiReachable -or
                -not $result.frontendReachable -or ($RequireAnalysis -and -not $result.demoIndexReady))) {
    throw 'RepoMind is not ready; inspect the readiness fields above.'
}
