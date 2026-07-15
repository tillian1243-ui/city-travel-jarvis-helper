# Jarvis Plugin Contract v0.1.0

Статус: **frozen for City MVP**  
Дата: 2026-07-14

## 1. Цель

Контракт отделяет Home Jarvis от внутренних API специализированных Helper-сервисов. Home знает только API Gateway. Gateway обнаруживает плагины по manifest и вызывает их через единый envelope.

Добавление нового плагина не требует изменения:

- Instructions Home Jarvis;
- OpenAPI Home Jarvis;
- клиентского способа авторизации;
- политики подтверждения записей.

## 2. Обязательные endpoint

### `GET /api/jarvis/manifest`

Возвращает описание домена, capabilities и политику записи. Endpoint защищается service-to-service Bearer key. Допускается открытый health, но manifest содержит детали архитектуры и по умолчанию закрыт.

### `POST /api/jarvis/read`

Выполняет одну read capability. Не должен изменять постоянное состояние. Допустимы краткоживущий cache и технический access log без чувствительного payload.

### `POST /api/jarvis/write/preview`

Готовит неизменяемый preview. Не пишет доменные данные. Возвращает подписанный `commit_token`, TTL, digest и полный write diff.

### `POST /api/jarvis/write/commit`

Принимает только ранее выданный `commit_token` и `confirmed=true`. Plugin обязан проверить подпись, TTL, одноразовость и digest. Commit не может дополнять или переинтерпретировать preview.

## 3. Capability IDs

Формат: `<domain>.<noun>.<verb>` либо `<domain>.<verb>`.

Примеры:

- `work.context.resume`
- `fitness.program.current`
- `finance.statement.import`
- `city.place.search`
- `city.route.cycling`

Capability должна быть стабильной семантической операцией. Внутренний URL плагина может меняться без изменения capability ID.

## 4. Request envelope

Обязательные поля:

- `contract_version` — `0.1.0`;
- `request_id` — уникальный ID Gateway;
- `capability` — ID из manifest;
- `payload` — доменные параметры.

Опционально:

- `trace_id` — сквозная трассировка;
- `attachments` — временные references;
- `context.user_intent` — исходный смысл запроса пользователя;
- `context.dry_run` — запрет записи независимо от capability.

Плагин не должен доверять только названию capability: режим read/write проверяется по собственному manifest и серверной политике.

## 5. Response envelope

Статусы:

- `ok` — read выполнен полностью;
- `partial` — ответ полезен, но часть источников недоступна;
- `needs_input` — нужны уточнения;
- `preview_ready` — сформирован preview;
- `committed` — запись выполнена;
- `rejected` — политика или данные запрещают действие;
- `error` — техническая ошибка.

Каждый ответ содержит:

- идентичность и версию плагина;
- `data`;
- предупреждения;
- источники;
- freshness для изменяемых данных;
- вопросы, если нужны уточнения.

## 6. Write safety

Для `preview_confirm_commit` обязательны:

1. Preview ничего не пишет.
2. Commit вызывается отдельным пользовательским сообщением.
3. Token подписан отдельным secret, не API key.
4. Token имеет TTL.
5. Token одноразовый.
6. Token связан с digest полного preview.
7. После рестарта потерянный in-memory preview не восстанавливается догадкой.
8. Commit возвращает audit ID и фактически записанные counts.
9. Если `WRITES_ENABLED != true`, commit отклоняется.
10. Любой `dry_run=true` запрещает commit.

Work plugin публикует `read_only`; write endpoint обязан отвечать `rejected`, даже если его вызвали напрямую.

## 7. Attachments

В v0.1 поддерживаются только временные references:

- Gateway получает attachment от клиента;
- проверяет allowlist MIME/type/size;
- передаёт плагину временную ссылку или проксирует bytes;
- plugin не сохраняет исходный документ без явно подтверждённой доменной политики;
- secrets, полные банковские реквизиты и адреса не должны попадать в логи.

`openaiFileIdRefs` является транспортом Custom GPT → Gateway, но не частью доменного контракта. Gateway преобразует его в `attachments[]`.

## 8. Sources and freshness

Для live-данных plugin возвращает `freshness.as_of`. Источники маркируются типом и уверенностью. Производные выводы получают source type `derived` и не маскируются под факт.

City обязан различать:

- актуально проверенное время работы;
- исторические/сохранённые сведения;
- пользовательские воспоминания;
- расчётный маршрут.

## 9. Errors

Минимальные codes:

- `CAPABILITY_NOT_FOUND`
- `INVALID_REQUEST`
- `AUTH_FAILED`
- `UPSTREAM_UNAVAILABLE`
- `SOURCE_STALE`
- `ATTACHMENT_REJECTED`
- `WRITES_DISABLED`
- `CONFIRMATION_REQUIRED`
- `PREVIEW_EXPIRED`
- `PREVIEW_NOT_FOUND`
- `COMMIT_TOKEN_INVALID`
- `DUPLICATE_COMMIT`
- `POLICY_REJECTED`

`retryable=true` ставится только для действительно временных ошибок.

## 10. Security

- Gateway и plugin используют разные API keys.
- Secrets хранятся только в Railway Variables.
- Manifest не публикует URLs upstream-систем и secrets.
- Plugin не принимает произвольный target URL из payload.
- SSRF-защита обязательна для временных attachment URLs.
- Логи: request_id, capability, duration, status; без содержимого финансовых, медицинских и рабочих документов.
- Autonomous actions всегда `false` в текущей экосистеме.

## 11. Backward compatibility

Совместимые изменения без смены contract version:

- новая capability;
- новое необязательное поле;
- новый warning code;
- новая версия plugin.

Несовместимые:

- удаление обязательного поля;
- изменение смысла статуса;
- изменение preview/commit модели;
- изменение формата capability routing.

## 12. Adapter strategy for existing plugins

Work, Fitness и Finance сохраняют текущие endpoint для прямых GPT. Поверх них добавляется тонкий contract adapter:

- map capability → существующая service function;
- оборачивает результат в response envelope;
- не дублирует бизнес-логику;
- не ослабляет доменную write policy.

Адаптацию существующих трёх сервисов откладываем до Gateway MVP. City реализуется по контракту сразу.
