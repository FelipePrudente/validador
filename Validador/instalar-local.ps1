# Instala o validador em C:\ValidadorDOE para rodar sem login do usuário.
# Execute no PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\instalar-local.ps1

$ErrorActionPreference = "Stop"

$sourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetDir = "C:\ValidadorDOE"
$python = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $python) {
    throw "Python não encontrado no PATH."
}

Write-Host "Instalando validador em: $targetDir" -ForegroundColor Cyan

if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
}

$exclude = @("logs", "__pycache__", ".git")
Get-ChildItem $sourceDir -Force | Where-Object {
    $_.Name -notin $exclude
} | ForEach-Object {
    $dest = Join-Path $targetDir $_.Name
    if ($_.PSIsContainer) {
        if ($_.Name -eq "validador") {
            Copy-Item $_.FullName $dest -Recurse -Force
        }
    } else {
        Copy-Item $_.FullName $dest -Force
    }
}

if (-not (Test-Path (Join-Path $targetDir "config.json"))) {
    Copy-Item (Join-Path $sourceDir "config.example.json") (Join-Path $targetDir "config.json") -Force
    Write-Warning "config.json criado a partir do exemplo. Configure o webhook do Teams."
}

$paths = @{
    python = $python
    project_dir = $targetDir
} | ConvertTo-Json

$paths | Set-Content (Join-Path $targetDir "paths.json") -Encoding UTF8

Write-Host "Arquivos copiados." -ForegroundColor Green
Write-Host "Python: $python"
Write-Host ""
Write-Host "Agora configure a tarefa sem necessidade de login..." -ForegroundColor Cyan

Set-Location $targetDir
& (Join-Path $targetDir "agendar.ps1") -SemLogin
