# City & Travel Jarvis v1.0.2 hotfix

Исправляет HTTP 500 при preview впечатлений, когда Custom GPT передаёт название места строкой или ratings не в идеальной тестовой форме.

## Причина

Backend ожидал `place` только как объект `{name, city}` и вызывал `.get()` у строки. Generic payload в OpenAPI не заставлял GPT соблюдать эту форму.

## После обновления

- natural payload нормализуется;
- malformed payload возвращает `needs_input / INVALID_REQUEST`;
- неожиданный preview failure возвращает structured error вместо сырого HTTP 500;
- canonical experience JSON закреплён в Instructions и Action schema.
