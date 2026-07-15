# City & Travel Jarvis v1.0.5 — Drive OAuth для личного Google Drive

## Зачем это нужно

Google service account продолжает работать с Google Sheets, но не может владеть файлами в обычном `My Drive`: у service account нет собственного Drive quota. Для GPX/KML/PDF используется OAuth конкретного пользователя.

Архитектура после исправления:

```text
Google Sheets -> service account (без изменений)
Google Drive exports -> user OAuth refresh token
```

Запрашивается только scope `drive.file`. Скрипт создаёт отдельную папку, принадлежащую пользователю, и Helper получает доступ только к файлам, созданным этим OAuth-приложением.

## 1. Создать OAuth client

В том же Google Cloud project, где включён Google Drive API:

1. Открой `Google Auth Platform`.
2. Заполни минимальные Branding / Audience данные.
3. В Data Access добавь scope:

```text
https://www.googleapis.com/auth/drive.file
```

4. В Clients создай:

```text
OAuth client ID -> Desktop app
```

5. Скачай JSON в `Downloads`.

Для постоянной работы переведи приложение из `Testing` в `In production`. В Testing пользовательская авторизация и refresh token истекают через семь дней.

## 2. Получить refresh token и папку

Из папки репозитория:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup-drive-oauth.ps1
```

Скрипт:

- откроет Google consent в браузере;
- запросит только `drive.file`;
- создаст `City Jarvis Files (OAuth)`;
- откроет временный файл с Railway Variables.

## 3. Добавить Railway Variables

Добавь или замени:

```text
GOOGLE_DRIVE_AUTH_MODE=user_oauth
GOOGLE_DRIVE_OAUTH_CLIENT_ID=...
GOOGLE_DRIVE_OAUTH_CLIENT_SECRET=...
GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN=...
GOOGLE_DRIVE_FOLDER_ID=...
```

Не меняй:

```text
GOOGLE_SERVICE_ACCOUNT_JSON_B64
GOOGLE_SPREADSHEET_ID
STORAGE_MODE=google_sheets
```

После обновления Variables Railway выполнит redeploy.

## 4. Проверить setup

```powershell
Invoke-RestMethod `
  -Uri "$domain/api/setup/validate" `
  -Method Get `
  -Headers $headers |
  ConvertTo-Json -Depth 20
```

Ожидается:

```text
ready: true
sheets_ready: true
exports_ready: true
drive.auth_mode: user_oauth
drive.code: OK
```

## 5. Повторить экспорт

Старые preview могли исчезнуть после redeploy. Создай новый preview экспорта и отдельно подтверди его точный `PRE-...`.

## 6. Удалить временные секреты

```powershell
Remove-Item "$env:TEMP\city-jarvis-drive-oauth.env" -ErrorAction SilentlyContinue
```

OAuth client JSON храни локально в защищённой папке и не загружай в GitHub.
