param(
    [string]$OllamaUrl = 'http://127.0.0.1:11434',
    [string]$PythonUrl = 'http://127.0.0.1:8000',
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
$frontend = $false
try { $frontend = (Invoke-WebRequest -Uri $FrontendUrl -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 }
catch { $frontend = $false }
$browserApi = if ($frontend) { Probe "$($FrontendUrl.TrimEnd('/'))/api/health" } else { $null }
$analysis = if ($python) { Probe "$($PythonUrl.TrimEnd('/'))/analysis/status" } else { $null }
$modelAvailable = [bool]($ollama -and @($ollama.models | Where-Object name -eq $Model).Count -gt 0)
$indexReady = [bool]($analysis -and $analysis.analysisReady -eq $true -and $analysis.repositoryPath -and
    [IO.Path]::GetFullPath($analysis.repositoryPath) -eq [IO.Path]::GetFullPath($expected))
$result = [pscustomobject]@{
    ollamaReachable = [bool]$ollama
    requiredModelAvailable = $modelAvailable
    pythonApiReachable = [bool]($python -and $python.status -eq 'ok')
    frontendApiReachable = [bool]($browserApi -and $browserApi.status -eq 'ok' -and $browserApi.service -eq 'python-service')
    frontendReachable = $frontend
    demoIndexReady = $indexReady
    analyzedRepository = if ($analysis) { $analysis.repositoryPath } else { $null }
    expectedRepository = $expected
}
Write-Output $result
if ($Strict -and (-not $result.ollamaReachable -or -not $result.requiredModelAvailable -or
                -not $result.pythonApiReachable -or -not $result.frontendApiReachable -or
                -not $result.frontendReachable -or ($RequireAnalysis -and -not $result.demoIndexReady))) {
    throw 'RepoMind is not ready; inspect the readiness fields above.'
}
