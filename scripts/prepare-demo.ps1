param(
    [ValidateSet('inventory', 'register', 'price')][string]$Demo = 'inventory',
    [string]$PythonUrl = 'http://127.0.0.1:8000'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$relative = @{
    inventory = 'demo/order-demo'
    register = 'demo/repomind-agent-test-demo/call-chain-demo'
    price = 'demo/repomind-agent-test-demo/logic-bug-demo'
}
$repository = (Resolve-Path (Join-Path $root $relative[$Demo])).Path
$base = $PythonUrl.TrimEnd('/')
$body = @{ path = $repository } | ConvertTo-Json
$analysis = Invoke-RestMethod -Uri "$base/analysis/repository" -Method Post -ContentType 'application/json; charset=utf-8' -Body $body -TimeoutSec 60
$status = Invoke-RestMethod -Uri "$base/analysis/status" -TimeoutSec 5
if ($analysis.analysisReady -ne $true -or $status.analysisReady -ne $true -or
    [IO.Path]::GetFullPath($status.repositoryPath) -ne [IO.Path]::GetFullPath($repository)) {
    throw "Demo analysis did not become ready for $repository"
}
Write-Host "[$Demo] analysis ready: $repository"
Write-Host "files=$($analysis.sourceFileCount) symbols=$($analysis.symbolCount) resolvedCalls=$($analysis.resolvedCallCount) unresolvedCalls=$($analysis.unresolvedCallCount)"
Write-Output $analysis
