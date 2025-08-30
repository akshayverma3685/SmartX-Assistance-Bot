# 🎮 Handlers Overview

Handlers define bot features. Each module exports `register(dp)`.

## Core Handlers
- **start.py** → `/start` command, language selection
- **menu.py** → Main menu navigation
- **ai.py** → AI tools (chat, summarization, etc.)
- **downloader.py** → Media download (YT, Twitter, etc.)
- **tools.py** → Utilities (QR, text tools)
- **business.py** → Business tools (invoice, payment)
- **entertainment.py** → Fun features
- **premium.py** → Subscription and Razorpay integration
- **profile.py** → User profile, usage stats
- **admin.py** → Owner/admin-only commands

---
📝 Handlers are **dynamically registered** in `bot.py` so missing modules don’t break startup.
