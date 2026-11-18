# Agenda a validação do DOE-SP de segunda a sexta.
#
# Modo normal (precisa estar logado):
#   .\agendar.ps1
#   .\agendar.ps1 -Horario "08:30"
#
# Modo sem login (PC ligado, usuário não precisa estar logado):
#   .\agendar.ps1 -SemLogin
#   ou use: .\instalar-local.ps1

param(
    [switch]$SemLogin,
    [string]$Horario = "07:00"
)

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$wrapperScript = Join-Path $projectDir "executar.ps1"
$configFile = Join-Path $projectDir "config.json"
$python = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $python) {
    $pathsFile = Join-Path $projectDir "paths.json"
    if (Test-Path $pathsFile) {
        $python = (Get-Content $pathsFile -Raw | ConvertFrom-Json).python
    }
}

if (-not $python -or -not (Test-Path $python)) {
    throw "Python não encontrado. Instale o Python 3 e tente novamente."
}

if (-not (Test-Path $wrapperScript)) {
    throw "Arquivo executar.ps1 não encontrado em: $projectDir"
}

if (-not (Test-Path $configFile)) {
    throw "Arquivo config.json não encontrado. Copie config.example.json para config.json."
}

$config = Get-Content $configFile -Raw | ConvertFrom-Json
if ($config.teams.enabled -and ($config.teams.webhook_url -like "COLE_AQUI*")) {
    Write-Warning "O webhook do Teams ainda não foi configurado em config.json."
}

if ($SemLogin -and $projectDir -like "*OneDrive*") {
    Write-Warning "O projeto está no OneDrive. Para rodar sem login, use .\instalar-local.ps1"
    Write-Warning "O OneDrive geralmente não fica disponível quando você não está logado."
}

$taskName = "ValidadorDOE-SP"
$argument = '-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $wrapperScript
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $argument `
    -WorkingDirectory $projectDir

$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday, Tuesday, Wednesday, Thursday, Friday `
    -At $Horario

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun

if ($SemLogin) {
    Write-Host ""
    Write-Host "Modo: executar mesmo sem login do usuário" -ForegroundColor Cyan
    Write-Host "Informe a senha da sua conta Windows ($env:USERDOMAIN\$env:USERNAME)."
    Write-Host "Ela será salva de forma segura no Agendador de Tarefas."
    Write-Host ""

    $cred = Get-Credential -UserName "$env:USERDOMAIN\$env:USERNAME" -Message "Senha do Windows para a tarefa agendada"

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -User $cred.UserName `
        -Password $cred.GetNetworkCredential().Password `
        -RunLevel Limited `
        -Description "Valida cadernos e seções do Diário Oficial do Estado de São Paulo." `
        -Force | Out-Null

    $modo = "Sem login (credenciais salvas)"
} else {
    $principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive `
        -RunLevel Limited

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Valida cadernos e seções do Diário Oficial do Estado de São Paulo." `
        -Force | Out-Null

    $modo = "Com login (sessão interativa)"
}

Write-Host ""
Write-Host "Tarefa agendada com sucesso!" -ForegroundColor Green
Write-Host "Nome da tarefa : $taskName"
Write-Host "Modo           : $modo"
Write-Host "Horário        : segunda a sexta às $Horario"
Write-Host "Usuário        : $env:USERDOMAIN\$env:USERNAME"
Write-Host "Projeto        : $projectDir"
Write-Host "Python         : $python"
Write-Host "Logs           : $projectDir\logs"
Write-Host ""
Write-Host "Requisitos para rodar sem login:"
Write-Host "  - PC ligado no horário agendado"
Write-Host "  - Projeto em pasta local (ex.: C:\ValidadorDOE)"
Write-Host "  - Rede disponível para API do DOE e Teams"
Write-Host ""
Write-Host "Comandos úteis:"
Write-Host "  Get-ScheduledTask -TaskName '$taskName'"
Write-Host "  Start-ScheduledTask -TaskName '$taskName'"
Write-Host @'
  Unregister-ScheduledTask -TaskName 'ValidadorDOE-SP' -Confirm:$false
'@
Write-Host ""
