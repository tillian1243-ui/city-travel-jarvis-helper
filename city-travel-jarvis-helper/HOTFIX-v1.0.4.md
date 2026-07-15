# Hotfix v1.0.4

## Причина

Custom GPT иногда передавал `context.dry_run=true` в write-preview, потому что пользователь просил «ничего не записывай». Backend сохранял этот флаг в preview и затем закономерно отклонял отдельный подтверждённый commit как `POLICY_REJECTED`.

Это была неверная семантика: endpoint `/api/jarvis/write/preview` и так не пишет данные. Реальной границей безопасности является отдельный вызов commit с `confirmed=true`.

## Исправление

- write-preview всегда сохраняется как committable;
- исходный флаг остаётся только диагностическим `requested_dry_run`;
- commit больше не отклоняет корректный preview из-за этого флага;
- Instructions/OpenAPI требуют опускать `dry_run` или передавать `false` для write-preview;
- добавлены regression-тесты для token и preview_id.
