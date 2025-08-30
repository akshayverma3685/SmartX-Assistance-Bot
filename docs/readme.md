# 🤖 SmartX Assistance Bot

[![CI/CD](https://github.com/akshayverma3685/SmartX-Assistance-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/smartx-bot/actions)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/yourusername/smartx-bot)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)
[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/yourusername/smartx-bot)
[![Docker Pulls](https://img.shields.io/docker/pulls/yourdockerhub/smartx-bot.svg)](https://hub.docker.com/r/yourdockerhub/smartx-bot)
[![License](https://img.shields.io/github/license/yourusername/smartx-bot)](LICENSE)

SmartX Assistance Bot is a **production-ready Telegram bot** built with **Aiogram 3.x**.  
It includes **AI tools, media downloaders, business utilities, premium features, and admin panel**.  

---

## ✨ Features
- ✅ Modular handlers (`handlers/`)
- ✅ Service layer (`services/`)
- ✅ Database support (Postgres / MongoDB)
- ✅ Payment integration (Razorpay)
- ✅ Admin panel (`admin-panel/`)
- ✅ Structured logging (`logs/`)
- ✅ CI/CD ready (GitHub Actions workflows)
- ✅ Flexible deployment (Polling / Webhook)
- 
---

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/smartx-bot.git
cd smartx-bot

2. Create Virtual Environment

python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows

3. Install Dependencies

pip install -r requirements.txt

4. Setup Environment Variables

Create .env file:

BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/smartx
OWNER_ID=123456789
RUN_MODE=polling
LOG_LEVEL=INFO
WEBHOOK_URL=https://yourdomain.com/webhook

5. Run the Bot

python bot.py


---

🚀 Deployment Guide

🌐 Railway (Recommended)



1. Fork this repo


2. Go to Railway → New Project → Deploy repo


3. Add environment variables in Railway Dashboard


4. Done ✅




---

🌐 Render



1. Go to Render


2. New → Web Service → Connect repo


3. Build Command:

pip install -r requirements.txt

Start Command:

python bot.py


4. Add environment variables


5. Deploy ✅




---

🌐 Heroku



heroku create smartx-bot
heroku config:set BOT_TOKEN=xxx DATABASE_URL=xxx OWNER_ID=123456789
git push heroku main


---

🐳 Docker

docker build -t smartx-bot .
docker run -d --env-file .env smartx-bot


---

🖥️ VPS (Ubuntu 20.04+)

sudo apt update && sudo apt install python3-pip python3-venv git -y
git clone https://github.com/yourusername/smartx-bot.git
cd smartx-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nohup python3 bot.py &


---

🔄 CI/CD Workflow

This repo includes a GitHub Actions workflow (.github/workflows/ci.yml):

Install dependencies

Run flake8 linting

Run black --check formatting

Run pytest


✅ If workflow is green → Repo is ready for deployment.


---

📜 Logging

Logs are stored in logs/ folder:

bot.log → General activity

error.log → Errors & exceptions

payments.log → Payment-related activity

usage.log → User interactions



---

🐞 Troubleshooting

Bot crashes on startup → Run python -m compileall .

SyntaxError: unterminated string → Check string quotes

Database errors → Verify DATABASE_URL

Bot not responding → Check BOT_TOKEN & Telegram API status



---

👨‍💻 Maintainers

Developed by Akshay Verma
📬 Contact: Open GitHub Issue
