# Changelog

## 1.0.4

- Исправлен ложный `POLICY_REJECTED` после корректного отдельного подтверждения preview.
- `context.dry_run=true` больше не делает write-preview незаписываемым: endpoint preview и так ничего не меняет.
- Отдельный `confirmed=true` commit остаётся единственной границей записи.
- Instructions и OpenAPI явно запрещают трактовать фразу «ничего не записывай» как `dry_run=true`.
- Добавлены regression-тесты commit по token и preview_id после preview с `dry_run=true`.

## 1.0.3

- `preview_id` стал основным устойчивым идентификатором commit между сообщениями GPT Actions.
- Commit поддерживает `preview_id` без обязательного `commit_token`; подписанный token сохранён как дополнительный вариант.
- Preview явно возвращает confirmation-инструкцию и включает Preview ID в summary.
- `preview_id` остаётся одноразовым, TTL-bound и capability-bound.
- Для впечатлений больше не выдумывается сегодняшняя дата визита.
- HOME_CITY больше не подставляется как город исторического посещения; нужен реальный город или однозначное сохранённое место.
- Известные места Bistro22, Cheese Wizard, «Кофе на кухне», Ockam и «Сайго» закреплены за Санкт-Петербургом в Instructions.
- Уточнено сохранение пользовательского комментария без сочинённых формулировок.
- Добавлены regression tests cross-turn commit.

## 1.0.2

- Нормализация natural-language payload для `city.experience.record`.
- `place` теперь допускается как строка или объект; город по умолчанию — Москва.
- `ratings` допускается как массив, одиночный объект или карта Andrew/Katya.
- Ошибки формы payload возвращаются как `needs_input`, а не HTTP 500.
- Добавлен безопасный structured error для неожиданных ошибок preview.
- Добавлены smoke/regression tests для solo/couple natural payload.

## 1.0.1
- Исправлена потеря `commit_token` в GPT Actions: токен и preview ID теперь возвращаются и в явной response-схеме, и на верхнем уровне ответа.
- Уточнена политика подтверждения: подтверждение никогда не создаёт новый preview.
- Москва закреплена как рабочая локация и `Europe/Moscow` как часовой пояс по умолчанию.
- Запрос на смену контекстной локации больше не трактуется как автоматическая запись `city.rule.save`.

## 1.0.0
- Первый полный релиз City & Travel Jarvis.
