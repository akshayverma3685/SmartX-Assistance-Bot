---

### 📄 `docs/config.md`
```markdown
# ⚙️ Configuration Guide

The `config.py` file loads environment variables using `python-dotenv`.

## Mandatory Variables
- **BOT_TOKEN** → Telegram Bot API token
- **OWNER_ID** → Telegram User ID of bot owner
- **RUN_MODE** → `polling` or `webhook`

## Optional Variables
- **DATABASE_URL** → Postgres / MongoDB connection URI
- **LOG_LEVEL** → Logging level (`DEBUG`, `INFO`, `ERROR`)
- **WEBHOOK_URL**, **WEBAPP_HOST**, **WEBAPP_PORT** → Required in webhook mode
