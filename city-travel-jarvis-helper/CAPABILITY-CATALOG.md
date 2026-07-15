# Capability Catalog — City & Travel Jarvis v1.0.0

Все запросы к plugin API используют единый конверт:

```json
{
  "contract_version": "0.1.0",
  "request_id": "REQ-unique-id",
  "capability": "city.cockpit",
  "locale": "ru-RU",
  "timezone": "Europe/Moscow",
  "payload": {},
  "context": {"user_intent": "...", "dry_run": false}
}
```

## Read capability

### `city.cockpit` — STABLE
Сводка по местам, посещениям, поездкам, маршрутам и зрелости функций.

### `city.place.search` — STABLE
Ранжирует актуальные кандидаты, найденные GPT через Web Search. Обязателен `payload.candidates`; Helper сам интернет не ищет.

Полезные поля кандидата:

```json
{
  "name": "Название",
  "city": "Москва",
  "address": "...",
  "open_now": true,
  "walk_minutes": 12,
  "price_level": 2,
  "rating": 4.7,
  "fit_tags": ["solo", "after_gym"],
  "is_chain_in_home_city": false,
  "status": "OPEN",
  "source_url": "https://...",
  "checked_at": "2026-07-14T18:30:00+03:00",
  "confidence": "high"
}
```

Контекст поиска может включать `city`, `context`, `budget_level`, `max_walk_minutes`, `is_travel`.

### `city.place.list` — STABLE
Фильтрует сохранённые места по городу, статусу и текстовому запросу.

### `city.experience.summary` — STABLE
Возвращает посещения, отдельные оценки Andrew и Katya, `WouldReturn`, блюда и couple verdict.

### `city.trip.plan` — STABLE
Проверяет предложенный план поездки без записи: пересечения по времени, логистические разрывы, запасные планы.

### `city.trip.get` — STABLE
Возвращает сохранённую поездку, дни и itinerary items.

### `city.trip.next` — STABLE
Режим «что дальше»: активный, следующий и последующие блоки плана плюс fallback.

### `city.route.walking` — BETA
Оценивает дистанцию и ожидаемое время пешей прогулки.

### `city.route.cycling` — BETA
Оценивает время по велосипедному профилю, риски, bailout points и новизну. По умолчанию используется профиль Andrew: Stern Motion 4.0, 12–15 км/ч, 60–80 минут.

### `city.route.photowalk` — BETA
Оценивает фотомаршрут. Для качественного результата передаётся `light_context` и точки с координатами.

### `city.route.literary` — BETA
Проверяет литературный/исторический маршрут и предупреждает о точках с низкой уверенностью. В каждой точке желательно передавать `confidence`, `source_url` и тип утверждения.

### `city.route.get` — STABLE
Возвращает сохранённый маршрут, точки и ссылки экспорта.

### `city.event.rank` — ADVISORY
Ранжирует актуальные события из веб-поиска с учётом цены, дороги, интересов и наличия билетов.

### `city.area.compare` — BETA
Сравнивает районы проживания по переданным оценкам и весам: transport, food, noise, cost, plan_fit.

### `city.weather.adapt` — ADVISORY
Адаптирует план по переданному актуальному forecast: дождь, ветер, жара, холод.

### `city.logistics.departure` — BETA
Считает реальное время выхода с дорогой, буфером, багажом и контролем.

### `city.maturity.status` — STABLE
Показывает реальные тесты, проблемы и рекомендации по повышению зрелости.

## Write preview capability

Каждая запись сначала вызывается через `/api/jarvis/write/preview`. Ответ содержит `preview_id`, `commit_token`, digest и точный diff. В том же сообщении commit запрещён.

### `city.place.save`
Сохранение или обновление места и метаданных свежести.

### `city.place.status`
Изменение статуса: WANT_TO_VISIT, SHORTLISTED, PLANNED, VISITED, LIKED, FAVORITE, NOT_FOR_ME, CLOSED, RECHECK_NEEDED.

### `city.place.preference`
Сигнал о месте: понравилось, дороговато одному, подходит после зала и т.п.

### `city.experience.record`
Одиночное или совместное посещение. Оценки Andrew и Katya хранятся отдельно.

Минимальный solo payload:

```json
{
  "place": {"name": "Bistro22", "city": "Санкт-Петербург"},
  "visit_date": "2026-07-09",
  "context": "solo",
  "ratings": [
    {"person": "Andrew", "overall_rating": 9, "would_return": "YES"}
  ]
}
```

Пример couple:

```json
{
  "place_id": "PLC-...",
  "context": "couple",
  "party": "Andrew, Katya",
  "ratings": [
    {"person": "Andrew", "overall_rating": 8, "would_return": "YES"},
    {"person": "Katya", "overall_rating": 7, "would_return": "MAYBE"}
  ],
  "items": [
    {"person": "Andrew", "name": "Блюдо", "rating": 9, "would_order_again": true}
  ]
}
```

### `city.trip.save`
Сохраняет карточку поездки, дни и элементы маршрута.

### `city.trip.update`
Перестраивает активную поездку или статусы отдельных itinerary items.

### `city.route.save`
Сохраняет маршрут и упорядоченные точки с координатами.

### `city.route.export`
Создаёт GPX/KML/PDF в папке Google Drive и записывает ссылки в Routes.

### `city.event.save`
Сохраняет только выбранное событие, а не всю найденную афишу.

### `city.rule.save`
Сохраняет подтверждённое персональное правило рекомендаций.

### `city.journal.record`
Сохраняет короткий итог дня или поездки.

### `city.maturity.feedback`
Фиксирует реальный тест capability. Переходы зрелости:

- ADVISORY → BETA: минимум 3 теста, ≥67% успешных, practical rating ≥6.5, без критических ошибок;
- BETA → STABLE: минимум 10 тестов, ≥80% успешных, accuracy ≥8, practical rating ≥8, без критических ошибок.

Автоматическое повышение по умолчанию отключено. Helper показывает рекомендацию; применять её лучше осознанно.
