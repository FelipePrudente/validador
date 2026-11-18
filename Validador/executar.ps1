# Wrapper usado pela Tarefa Agendada do Windows.
$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pathsFile = Join-Path $projectDir "paths.json"
$logDir = Join-Path $projectDir "logs"
$mainScript = Join-Path $projectDir "main.py"

if (Test-Path $pathsFile) {
    $paths = Get-Content $pathsFile -Raw | ConvertFrom-Json
    $python = $paths.python
} else {
    $python = (Get-Command python -ErrorAction Stop).Source
}

if (-not (Test-Path $python)) {
    throw "Python não encontrado em: $python"
}

if (-not (Test-Path $mainScript)) {
    throw "Arquivo main.py não encontrado em: $projectDir"
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("validador_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))

$env:PYTHONIOENCODING = "utf-8"
Set-Location $projectDir

# Redireciona via cmd para que stderr do Python não vire ErrorRecord
# e aborte a tarefa com $ErrorActionPreference=Stop.
$cmd = "`"$python`" `"$mainScript`""
cmd.exe /c "$cmd > `"$logFile`" 2>&1"
$exitCode = $LASTEXITCODE

Get-Content -Path $logFile -ErrorAction SilentlyContinue
exit $exitCode
