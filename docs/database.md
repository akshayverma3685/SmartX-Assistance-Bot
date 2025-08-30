---

### 📄 `docs/database.md`
```markdown
# 🗄️ Database

The bot supports **Postgres** via `asyncpg` or **MongoDB** (optional).

## Connection
- Defined in `core/database.py`
- Configurable with `DATABASE_URL`

## Recommended Schema
- **users** → Telegram user info, subscription status
- **premium** → Payments & subscriptions
- **logs** → Optional structured logs

## Migration
Use **Alembic** (Postgres) or custom init script.
