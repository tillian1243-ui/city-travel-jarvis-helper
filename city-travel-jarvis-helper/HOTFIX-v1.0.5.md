# Hotfix v1.0.5

- Google Sheets продолжает использовать service account.
- Drive exports поддерживают `GOOGLE_DRIVE_AUTH_MODE=user_oauth`.
- Добавлена локальная выдача refresh token с узким scope `drive.file`.
- Setup validation проверяет реальную папку Drive и возвращает `drive.code`.
- Service account + My Drive теперь определяется заранее как неподдерживаемая конфигурация.
- Shared Drive поддерживается через `supportsAllDrives=true`.
- Drive/commit errors возвращаются структурированно вместо сырого HTTP 500.
- Preview не потребляется после неуспешного commit.
