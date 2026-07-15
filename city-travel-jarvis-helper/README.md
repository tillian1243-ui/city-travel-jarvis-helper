# City & Travel Jarvis Helper v1.0.5

Личный backend для городских решений, поездок, маршрутов и памяти о местах.

City & Travel Jarvis не пытается заменить карты или веб-поиск. Custom GPT находит актуальные сведения в интернете, а Helper:

- ранжирует найденные места с учётом ситуации и личной памяти;
- проверяет планы поездок и предлагает следующий выполнимый шаг;
- оценивает пешие, велосипедные, фото- и литературные маршруты;
- хранит места, посещения, отдельные оценки Andrew и Katya, блюда и намерение вернуться;
- сохраняет поездки, маршруты, события, правила и журнал впечатлений;
- экспортирует GPX, KML и PDF в Google Drive;
- ведёт зрелость функций по реальным тестам;
- выполняет записи только через `preview → отдельное подтверждение → commit`.

## Архитектура

```text
City & Travel Jarvis (Custom GPT + Web Search)
            ↓ Bearer API key
City & Travel Jarvis Helper (Railway / FastAPI)
            ↓
Google Sheets — структурированная память
Google Drive — GPX, KML и PDF
```

Helper нативно реализует Jarvis Plugin Contract v0.1.0:

```text
GET  /api/jarvis/manifest
POST /api/jarvis/read
POST /api/jarvis/write/preview
POST /api/jarvis/write/commit
```

## Быстрый локальный запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ACTION_API_KEY = "local-test-key"
$env:PREVIEW_SIGNING_SECRET = "local-preview-secret-at-least-32-characters"
$env:STORAGE_MODE = "memory"
$env:WRITES_ENABLED = "true"
uvicorn app.main:app --reload
```

Проверка:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
```

## Основные capability

### Чтение и рекомендации

- `city.cockpit`
- `city.place.search`
- `city.place.list`
- `city.experience.summary`
- `city.trip.plan`
- `city.trip.get`
- `city.trip.next`
- `city.route.walking`
- `city.route.cycling`
- `city.route.photowalk`
- `city.route.literary`
- `city.route.get`
- `city.event.rank`
- `city.area.compare`
- `city.weather.adapt`
- `city.logistics.departure`
- `city.maturity.status`

### Контролируемые записи

- `city.place.save`
- `city.place.status`
- `city.place.preference`
- `city.experience.record`
- `city.trip.save`
- `city.trip.update`
- `city.route.save`
- `city.route.export`
- `city.event.save`
- `city.rule.save`
- `city.journal.record`
- `city.maturity.feedback`

Полный manifest доступен через `GET /api/jarvis/manifest` и лежит в `MANIFEST.json`.

## Хранилище

В production используется одна Google-таблица с нормализованными листами и одна папка Google Drive для файлов. Исходные веб-страницы, полная история геолокации и сырые разговоры не сохраняются.

## Безопасность

- `autonomous_actions=false`;
- фоновых задач нет;
- Helper не покупает билеты и не создаёт бронирования;
- Helper не выполняет непрерывное отслеживание местоположения;
- preview подписан и имеет TTL;
- commit одноразовый и должен совпасть с capability и digest preview;
- `WRITES_ENABLED=false` полностью блокирует commit.

Подробная установка: `SETUP-CITY-TRAVEL-JARVIS-v1.0.0.md`.


## Drive exports in My Drive

For a personal My Drive folder, keep Google Sheets on the service account and set `GOOGLE_DRIVE_AUTH_MODE=user_oauth`. See `SETUP-DRIVE-OAUTH-v1.0.5.md`. A service account can upload only to a Shared Drive, not to a human user's My Drive.
