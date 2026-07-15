# Contract decisions

## D-001 — Generic gateway endpoints

Принято: Home/Gateway используют четыре стабильных endpoint. Доменные API остаются внутренней реализацией.

Причина: новый Jarvis добавляется в registry без обновления Home OpenAPI.

## D-002 — Manifest is declarative, not executable schema

Manifest описывает capability и routing hints, но Gateway хранит allowlist plugin URLs и secrets. Plugin не может заставить Gateway вызвать произвольный endpoint.

## D-003 — Commit remains plugin-owned

Gateway не подписывает доменные previews и не реконструирует их. Token создаёт и валидирует plugin, потому что только он знает фактический write diff.

## D-004 — No cross-domain distributed transaction in v0.1

Home может собрать несколько previews, но commits подтверждаются и выполняются по доменам отдельно. Это исключает ложную атомарность между Google Sheets, Jira и другими источниками.

## D-005 — City first

City & Travel Jarvis реализует контракт нативно. Existing Work/Fitness/Finance получают adapters только перед Gateway MVP.
