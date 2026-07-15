# City & Travel Jarvis v1.0.0 — Release Notes

Первая полная версия персонального City & Travel контура.

## Вошло в релиз

### Live city intelligence

- ранжирование актуальных мест из Web Search;
- учёт часов работы, расстояния, бюджета, company context и личной памяти;
- защита от рекомендаций закрытых мест;
- штраф сетям домашнего города во время поездок;
- режимы solo, couple, friends, work, travel и after_gym.

### Place Memory и впечатления

- справочник мест;
- отдельные посещения;
- отдельные оценки Andrew и Katya;
- 1–10, YES/MAYBE/NO;
- оценки еды, атмосферы, сервиса и value;
- блюда и `WouldOrderAgain`;
- couple verdict без потери исходных оценок;
- статусы WANT_TO_VISIT, VISITED, FAVORITE, CLOSED и другие;
- персональные signals.

### Trips и What Next

- сохранение поездок, дней и itinerary items;
- проверка плана без записи;
- обнаружение пересечений;
- чтение сохранённой поездки;
- режим «что дальше»;
- перестройка активной поездки;
- rain/fatigue fallback.

### Routes

- walking;
- cycling;
- photowalk;
- literary & historical;
- расстояние и расчёт времени;
- велосипедный профиль Stern Motion 4.0, 12–15 км/ч;
- risk tags и bailout points;
- novelty percent;
- GPX, KML и PDF в Google Drive.

### Additional modes

- актуальные события;
- сравнение районов проживания;
- адаптация под погоду;
- реалистичный departure time с багажом и запасом;
- trip journal.

### Capability Maturity

- 17 STABLE;
- 9 BETA;
- 3 ADVISORY;
- реальные тесты и журнал проблем;
- рекомендации ADVISORY → BETA → STABLE;
- автоматическое повышение по умолчанию выключено.

### Plugin Contract

Нативная реализация Jarvis Plugin Contract v0.1.0:

```text
GET  /api/jarvis/manifest
POST /api/jarvis/read
POST /api/jarvis/write/preview
POST /api/jarvis/write/commit
```

Home Jarvis сможет подключить City через будущий Gateway без разрастания своей OpenAPI-схемы.

### Safety

- `autonomous_actions=false`;
- фоновых задач нет;
- запись только `preview → отдельное подтверждение → commit`;
- одноразовый подписанный commit-token;
- digest preview;
- `WRITES_ENABLED` kill switch;
- Write_Log;
- никаких покупок, оплат и бронирований;
- непрерывная геолокация не хранится.

## Тесты

- 26 automated tests;
- 6 уникальных GPT Action operations;
- проверена работа plugin manifest;
- проверены solo/couple ratings;
- проверены место, поездка, маршрут, export и maturity feedback;
- проверены запрет записи, dry-run и Bearer authorization;
- шаблон XLSX прошёл проверку структуры ZIP и скан формул без ошибок.

## Известные ограничения

- Helper сам не выполняет интернет-поиск: живые кандидаты и forecast должен подготовить Custom GPT через Web Search;
- crowd level, перекрытия, состояние покрытия и наличие билетов остаются Advisory, если нет свежего надёжного источника;
- route review не является turn-by-turn navigation;
- PDF v1 — компактный технический путеводитель;
- preview хранится в памяти и теряется при перезапуске сервиса;
- Google Sheets рассчитан на личное использование, а не на многопользовательскую систему.
