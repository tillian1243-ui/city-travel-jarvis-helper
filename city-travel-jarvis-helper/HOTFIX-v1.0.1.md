# City & Travel Jarvis v1.0.1 hotfix

## Исправленная проблема
Custom GPT мог не сохранить вложенный `preview.commit_token` из универсальной response-схемы и при подтверждении бесконечно создавать новые preview.

## Изменения
- `commit_token`, `preview_id`, `capability` и TTL продублированы на верхнем уровне preview-ответа.
- Для GPT Action добавлены явные `PluginResponse` и `PreviewDetails`.
- Instructions запрещают вызывать preview в ответ на подтверждение.
- Москва и Europe/Moscow закреплены как базовый контекст; текущая геолокация интерфейса не должна их переопределять.

## Обновление
1. Отправить содержимое helper v1.0.1 в тот же GitHub-репозиторий и дождаться redeploy Railway.
2. В Custom GPT заменить Instructions файлом v1.0.1.
3. В Action заменить schema файлом v1.0.1 и повторно сохранить Bearer-аутентификацию.
4. Создать новый preview и подтвердить его отдельным сообщением. Старые preview после redeploy недействительны.
