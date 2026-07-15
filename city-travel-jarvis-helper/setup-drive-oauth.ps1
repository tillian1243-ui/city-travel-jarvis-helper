param(
    [string]$ClientSecretJson,
    [string]$FolderName = "City Jarvis Files (OAuth)"
)

$ErrorActionPreference = "Stop"

if (-not $ClientSecretJson) {
    $candidate = Get-ChildItem -Path "$env:USERPROFILE\Downloads" -File |
        Where-Object { $_.Name -like "client_secret*.json" -or $_.Name -like "client*.json" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $candidate) {
        throw "OAuth client JSON не найден в Downloads. Передай путь через -ClientSecretJson."
    }
    $ClientSecretJson = $candidate.FullName
}

if (-not (Test-Path $ClientSecretJson)) {
    throw "Файл OAuth client JSON не найден: $ClientSecretJson"
}

$scriptPath = Join-Path $PSScriptRoot "scripts\create_drive_oauth_credentials.py"
$outputPath = Join-Path $env:TEMP "city-jarvis-drive-oauth.env"

Write-Host "Устанавливаю локальные OAuth-зависимости..." -ForegroundColor Cyan
python -m pip install --user google-auth-oauthlib google-api-python-client
if ($LASTEXITCODE -ne 0) {
    throw "Не удалось установить локальные OAuth-зависимости."
}

Write-Host "Открываю авторизацию Google..." -ForegroundColor Cyan
python $scriptPath $ClientSecretJson --folder-name $FolderName --output $outputPath
if ($LASTEXITCODE -ne 0) {
    throw "Не удалось получить Drive OAuth credentials."
}

Write-Host "`nГотово. Railway Variables открыты в Блокноте." -ForegroundColor Green
notepad $outputPath
