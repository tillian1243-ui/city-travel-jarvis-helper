# Changelog

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
