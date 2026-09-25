param([string]$PythonUrl = 'http://127.0.0.1:8000')

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$repository = (Resolve-Path (Join-Path $root 'demo/enterprise-order-showcase')).Path
$base = $PythonUrl.TrimEnd('/')
$body = @{ path = $repository } | ConvertTo-Json
$analysis = Invoke-RestMethod -Uri "$base/analysis/repository" -Method Post -ContentType 'application/json; charset=utf-8' -Body $body -TimeoutSec 120
$status = Invoke-RestMethod -Uri "$base/analysis/status" -TimeoutSec 5
if ($analysis.analysisReady -ne $true -or $status.analysisReady -ne $true -or
    [IO.Path]::GetFullPath($status.repositoryPath) -ne [IO.Path]::GetFullPath($repository)) {
    throw "Showcase analysis did not become ready for $repository"
}
Write-Host "[enterprise-order-showcase] analysis ready: $repository"
Write-Host "files=$($analysis.sourceFileCount) symbols=$($analysis.symbolCount) relations=$($analysis.relationCount) resolvedCalls=$($analysis.resolvedCallCount) unresolvedCalls=$($analysis.unresolvedCallCount)"
Write-Output $analysis
