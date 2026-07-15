# Установка City & Travel Jarvis v1.0.0

Эта инструкция ведёт от скачанного архива до первого безопасного сохранения места и экспорта маршрута.

## Что получится

```text
Custom GPT: City & Travel Jarvis
        ↓ Bearer API key
Railway: City & Travel Jarvis Helper
        ↓
Google Sheets: места, оценки, поездки и маршруты
Google Drive: GPX, KML и PDF
```

Используется отдельный сервисный аккаунт Google и отдельный Railway-сервис. Существующие Work, Fitness и Finance не меняются.

---

# Этап 1. Подготовить Google-таблицу

## 1.1 Загрузить шаблон

Скачай `city_travel_jarvis_data_source_v1.0.0.xlsx` и загрузи его в Google Drive.

Открой файл и выбери:

```text
Файл → Сохранить как Google Таблицы
```

Важно: Helper работает с нативной Google-таблицей, а не с Excel-файлом в режиме просмотра.

## 1.2 Получить Spreadsheet ID

Адрес выглядит так:

```text
https://docs.google.com/spreadsheets/d/1AbC...XYZ/edit
```

Скопируй часть между `/d/` и `/edit`. Это значение `GOOGLE_SPREADSHEET_ID`.

## 1.3 Ничего не переименовывать

В книге должны остаться листы:

```text
People
Places
Place_Experiences
Experience_Ratings
Experience_Items
Place_Signals
City_Preferences
Cycling_Profiles
Trips
Trip_Days
Itinerary_Items
Routes
Route_Points
Events
City_Rules
Trip_Journal
Capability_Maturity
Maturity_Test_Log
Search_History
Write_Log
Data_Quality
City_Config
```

`City Dashboard` предназначен для пользователя и не является обязательным системным листом.

Контрольная точка: Google-таблица открывается и в ней видны Andrew, Katya и велосипедный профиль.

---

# Этап 2. Создать папку для экспортов

В Google Drive создай папку:

```text
City Jarvis Files
```

В ней будут GPX, KML и PDF.

Открой папку. Адрес будет похож на:

```text
https://drive.google.com/drive/folders/1FolderId...
```

Часть после `/folders/` — это `GOOGLE_DRIVE_FOLDER_ID`.

Контрольная точка: папка создана, ID сохранён локально.

---

# Этап 3. Google Cloud и API

Можно использовать тот же Google Cloud project, что и для других Jarvis, но создай отдельный service account.

## 3.1 Включить API

В Google Cloud Console:

```text
APIs & Services → Library
```

Включи два API:

```text
Google Sheets API
Google Drive API
```

Sheets API нужен для таблицы. Drive API — для GPX/KML/PDF.

## 3.2 Создать service account

```text
IAM & Admin → Service Accounts → Create service account
```

Имя:

```text
city-jarvis-sheets
```

Роли уровня проекта выдавать не требуется.

## 3.3 Создать JSON-ключ

Открой service account:

```text
Keys → Add key → Create new key → JSON
```

Сохрани файл, например:

```text
C:\Users\tulte\Documents\Secrets\city-jarvis-service-account.json
```

Не загружай JSON в GitHub, чат или Google Drive.

## 3.4 Узнать email service account

В PowerShell:

```powershell
$key = Get-Content "C:\Users\tulte\Documents\Secrets\city-jarvis-service-account.json" -Raw | ConvertFrom-Json
$key.client_email
```

## 3.5 Выдать доступ

Расшарь на этот email:

1. именно новую City Google-таблицу;
2. папку `City Jarvis Files`.

Уровень доступа для обоих:

```text
Редактор
```

Контрольная точка: service account указан в доступах таблицы и папки.

---

# Этап 4. Преобразовать JSON в Base64

В PowerShell:

```powershell
$json = Get-Item "C:\Users\tulte\Documents\Secrets\city-jarvis-service-account.json"
$bytes = [System.IO.File]::ReadAllBytes($json.FullName)
$b64 = [Convert]::ToBase64String($bytes)
$b64.Length
```

Ожидается несколько тысяч символов.

Сохрани в временный файл:

```powershell
[System.IO.File]::WriteAllText(
  "$env:TEMP\city-jarvis-b64.txt",
  $b64,
  [System.Text.Encoding]::ASCII
)
```

Открыть:

```powershell
notepad "$env:TEMP\city-jarvis-b64.txt"
```

Внутри должна быть одна длинная строка. Это значение `GOOGLE_SERVICE_ACCOUNT_JSON_B64`.

Не присылай её в чат.

---

# Этап 5. GitHub

## 5.1 Распаковать архив

Распакуй `city-travel-jarvis-helper-v1.0.0.zip`.

Перейди в папку, где лежат `Dockerfile`, `requirements.txt` и каталог `app`:

```powershell
cd "C:\Users\tulte\Downloads\city-travel-jarvis-helper-v1.0.0\city-travel-jarvis-helper"
```

## 5.2 Создать пустой private repository

Рекомендуемое имя:

```text
city-travel-jarvis-helper
```

Не добавляй README или .gitignore при создании: они уже есть в архиве.

## 5.3 Отправить код

```powershell
git init
git add .
git commit -m "Initial City & Travel Jarvis v1.0.0"
git branch -M main
git remote add origin https://github.com/<USER>/city-travel-jarvis-helper.git
git push -u origin main
```

Проверка:

```powershell
git status
git remote -v
```

Контрольная точка: репозиторий private, код виден на GitHub, JSON-ключа там нет.

---

# Этап 6. Railway

## 6.1 Создать проект и сервис

В Railway:

```text
New Project → Deploy from GitHub repo
```

Выбери `city-travel-jarvis-helper`.

Dockerfile будет найден автоматически.

## 6.2 Создать секреты

В PowerShell сгенерируй два разных секрета:

```powershell
$actionKey = -join ((1..48 | ForEach-Object { Get-Random -Maximum 256 }) | ForEach-Object { $_.ToString("x2") })
$previewSecret = -join ((1..48 | ForEach-Object { Get-Random -Maximum 256 }) | ForEach-Object { $_.ToString("x2") })
$actionKey.Length
$previewSecret.Length
$actionKey -ne $previewSecret
```

Ожидается:

```text
96
96
True
```

Сохрани временно:

```powershell
@"
ACTION_API_KEY=$actionKey
PREVIEW_SIGNING_SECRET=$previewSecret
"@ | Set-Content "$env:TEMP\city-jarvis-secrets.txt"
notepad "$env:TEMP\city-jarvis-secrets.txt"
```

## 6.3 Добавить Railway Variables

Открой сервис:

```text
Variables → New Variable
```

Добавь:

```text
ACTION_API_KEY=<96-символьный ключ>
PREVIEW_SIGNING_SECRET=<другой 96-символьный ключ>
WRITES_ENABLED=false
STORAGE_MODE=google_sheets
GOOGLE_SPREADSHEET_ID=<ID таблицы>
GOOGLE_DRIVE_FOLDER_ID=<ID папки>
GOOGLE_SERVICE_ACCOUNT_JSON_B64=<одна длинная Base64-строка>
APP_TIMEZONE=Europe/Moscow
HOME_CITY=Москва
DEFAULT_MAP_PROVIDER=yandex
PREVIEW_TTL_SECONDS=1800
MAX_PLACE_CANDIDATES=30
MAX_ROUTE_POINTS=150
AUTO_PROMOTE_MATURITY=false
```

Сначала оставляем `WRITES_ENABLED=false`, пока не проверим чтение.

Не добавляй кавычки вокруг значений.

## 6.4 Создать публичный домен

```text
Settings → Networking → Generate Domain
```

Сохрани домен, например:

```text
https://city-travel-jarvis-helper-production.up.railway.app
```

## 6.5 Включить Serverless

Для личного использования:

```text
Settings → Deploy → Serverless → Enable
```

Первый запрос после сна может выполняться дольше.

Контрольная точка: последний deployment имеет статус Success.

---

# Этап 7. Проверить backend

В PowerShell:

```powershell
$domain = "https://ТВОЙ-ДОМЕН.up.railway.app"
$headers = @{ Authorization = "Bearer $actionKey" }
```

## 7.1 Health

```powershell
Invoke-RestMethod "$domain/health" | ConvertTo-Json -Depth 10
```

Ожидается:

```json
{"status":"ok","version":"1.0.0"}
```

## 7.2 Setup validation

```powershell
Invoke-RestMethod -Uri "$domain/api/setup/validate" -Method Get -Headers $headers |
  ConvertTo-Json -Depth 20
```

До включения записи ожидается:

```text
ready: true
sheets_ready: true
exports_ready: true
writes_enabled: false
```

У всех обязательных листов должен быть `status: ok`.

Если получен `403 The caller does not have permission`, проверь доступ service account к таблице и папке.

Если `exports_ready=false`, проверь `GOOGLE_DRIVE_FOLDER_ID`.

## 7.3 Включить запись

Только после `ready=true` измени Railway variable:

```text
WRITES_ENABLED=true
```

Дождись нового deployment и повтори setup validation. Нужно увидеть `writes_enabled: true`.

Контрольная точка: `ready=true`, `exports_ready=true`, `writes_enabled=true`.

---

# Этап 8. Создать Custom GPT

## 8.1 Основные настройки

Название:

```text
City & Travel Jarvis
```

Описание:

```text
Персональный помощник по местам, поездкам, прогулкам, веломаршрутам и памяти впечатлений.
```

Доступ:

```text
Только я
```

Включи Web Search. Он нужен для актуальных часов работы, закрытий, погоды, событий и маршрутов.

## 8.2 Instructions

Вставь полный текст файла:

```text
GPT-INSTRUCTIONS-city-travel-jarvis-v1.0.0-RU.txt
```

## 8.3 Action schema

Создай одно Action и вставь:

```text
openapi-action-city-travel-jarvis-v1.0.0.yaml
```

В схеме замени:

```text
https://YOUR-CITY-RAILWAY-DOMAIN
```

на реальный Railway-домен без завершающего `/`.

В схеме всего шесть операций, поэтому лимит GPT Actions не превышается.

## 8.4 Авторизация Action

```text
Authentication type: API Key
Auth type: Bearer
```

В поле ключа вставь только значение `ACTION_API_KEY`, без `ACTION_API_KEY=` и без кавычек.

Кнопка Authorize в Railway `/docs` не нужна. Авторизация настраивается внутри GPT Action.

Сохрани GPT.

---

# Этап 9. Smoke tests

## 9.1 Чтение

Отправь City Jarvis:

```text
Покажи City Cockpit и зрелость функций. Ничего не изменяй.
```

Ожидается вызов `city.cockpit` и нулевые пользовательские данные при наличии 17 STABLE, 9 BETA и 3 ADVISORY capability.

## 9.2 Live Place Search

```text
Найди на сегодня три несетевых места в Москве, где мне одному нормально поесть после зала. Проверь часы работы и цену. Ничего не сохраняй.
```

GPT должен сначала выполнить веб-поиск, затем передать candidates в `city.place.search`. Helper не должен отвечать пустым рейтингом.

## 9.3 Preview впечатления

```text
Я был один в Bistro22. Оценка 9/10, вернулся бы — да. Понравилась куриная грудка с трюфельным соусом и полбой. Подготовь preview, ничего не записывай.
```

Ожидается:

```text
status: preview_ready
requires_separate_confirmation: true
nothing_written: true
```

Убедись, что Katya не добавлена к solo-посещению.

Отдельным сообщением:

```text
Подтверждаю запись именно последнего preview без изменений.
```

После commit проверь `Place_Experiences`, `Experience_Ratings`, `Experience_Items` и `Write_Log`.

## 9.4 Couple ratings

```text
Мы с Катей были в тестовом месте. Андрей — 8/10 и YES, Катя — 6/10 и MAYBE. Подготовь preview, ничего не записывай.
```

Оценки должны быть двумя отдельными строками.

## 9.5 Route export

Сначала сохрани тестовый маршрут с минимум двумя координатами через preview/commit. Затем запроси preview экспорта в GPX, KML и PDF. После отдельного подтверждения ссылки должны появиться в `Routes`, а файлы — в папке Google Drive.

---

# Этап 10. После установки

Удалить временные файлы:

```powershell
Remove-Item "$env:TEMP\city-jarvis-secrets.txt" -ErrorAction SilentlyContinue
Remove-Item "$env:TEMP\city-jarvis-b64.txt" -ErrorAction SilentlyContinue
```

JSON-ключ храни только в защищённой локальной папке Secrets.

Создать стабильный тег после smoke tests:

```powershell
git tag -a v1.0.0 -m "Stable City & Travel Jarvis v1.0.0"
git push origin v1.0.0
```

---

# Частые ошибки

## `401 Unauthorized`
Проверь, что в GPT Action выбран API Key / Bearer и вставлен тот же `ACTION_API_KEY`, что в Railway.

## `403 The caller does not have permission`
Service account не получил Editor-доступ к Google-таблице или папке Drive.

## `ready=false`
Не хватает листа, лист переименован или таблица осталась `.xlsx`, а не стала нативной Google-таблицей.

## `Writes are disabled`
Выставь `WRITES_ENABLED=true` в нужном Production-сервисе и дождись deployment.

## `DRIVE_NOT_READY`
Нет `GOOGLE_DRIVE_FOLDER_ID`, папка не расшарена либо service account не имеет доступа.

## Place Search просит candidates
Это ожидаемо. Custom GPT должен сначала выполнить Web Search и передать актуальные варианты Helper.

## Старый commit_token не работает
Preview хранится в памяти и имеет TTL. Перезапуск Railway или истечение времени требует нового preview и нового отдельного подтверждения.

## Первый запрос медленный
Serverless будит контейнер. Повторный запрос обычно быстрее.
