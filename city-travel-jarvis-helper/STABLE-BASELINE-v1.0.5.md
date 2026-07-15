# City & Travel Jarvis v1.0.5 — Stable Baseline

Статус: ACCEPTED
Дата фиксации: 15 июля 2026 года
Backend version: 1.0.5
Plugin Contract: 0.1.0

## Архитектура

- отдельный Custom GPT City & Travel Jarvis;
- отдельный Railway Helper;
- Google Sheets через service account;
- Google Drive через user OAuth с scope drive.file;
- отдельные ключи и хранилище от Fitness, Finance и Work;
- интеграция с будущим Home Jarvis только через Gateway и Plugin Contract.

## Подтверждённые сценарии

- health и setup validation;
- доступ ко всем обязательным системным листам;
- City Cockpit и maturity status;
- live-поиск мест без автоматической записи;
- solo-посещение без добавления Katya;
- couple-посещение с раздельными оценками Andrew и Katya;
- дедупликация места при повторном посещении;
- preview → отдельное подтверждение → commit;
- сохранение маршрута и точек;
- экспорт маршрута в GPX, KML и PDF;
- запись ссылок Google Drive в Routes;
- чтение маршрута и экспортов после commit;
- Write_Log и Audit ID.

## Принятые правила безопасности

- autonomous_actions=false;
- запись только через preview и отдельный commit;
- явный Preview ID;
- WRITES_ENABLED kill switch;
- preview имеет TTL и хранится в памяти процесса;
- покупки, оплаты, бронирования и отмены не выполняются;
- непрерывная геолокация не хранится.

## Известные неблокирующие ограничения

- preview теряется после рестарта Railway;
- GPT иногда может повторять вводную фразу;
- GPT не должен сочинять пользовательские комментарии;
- оформление источников событий требует дальнейшей шлифовки;
- maturity real tests необходимо накапливать через реальные сценарии;
- AUTO_PROMOTE_MATURITY остаётся выключенным.

## Решение о релизе

Версия 1.0.5 считается стабильной базовой версией.
Новые изменения сначала накапливаются в backlog и выпускаются пакетно.
Рабочий backend не изменяется ради одиночных косметических правок.