# 🐞 Troubleshooting

## Common Issues
- **SyntaxError: unterminated string** → Check quotes in strings
- **ModuleNotFoundError** → Ensure handler/service file exists
- **Bot blocked by user** → Catch `TelegramForbiddenError`

## Debugging
- Run with `LOG_LEVEL=DEBUG`
- Check `logs/` folder if configured
- Use `pytest -v` for testing

## Emergency
If bot crashes on startup:
```bash
python -m compileall .
