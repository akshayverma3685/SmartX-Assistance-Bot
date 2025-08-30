# 🤖 SmartX Telegram Bot

SmartX is a **modular, scalable Telegram Bot** built with Python, supporting AI, downloads, entertainment, payments, business utilities, and an admin dashboard.  
It uses **MongoDB + PostgreSQL + Redis + MinIO (S3)** for storage, **Celery** for background tasks, and supports **Prometheus metrics**.

---

## ✨ Features
- 🔹 Multi-language support (English, Hindi)
- 🔹 MongoDB for bot state & user data
- 🔹 PostgreSQL for payments & audit logs
- 🔹 Redis for caching, Celery tasks, and anti-spam
- 🔹 MinIO (S3-compatible) for file storage
- 🔹 Modular handlers (`handlers/*`)
- 🔹 Admin Panel (`admin_panel/*`)
- 🔹 Monitoring with Prometheus
- 🔹 Worker for async tasks

---

## ⚙️ Requirements
- Python 3.10+
- Docker + Docker Compose
- Telegram Bot Token from [@BotFather](https://t.me/botfather)

---

## 🚀 Setup

### 1️⃣ Clone Repository
```bash
git clone https://github.com/yourusername/smartx-bot.git
cd smartx-bot

2️⃣ Environment Variables

Copy .env.example → .env and update values:

cp .env.example .env

Required values:

BOT_TOKEN=your_telegram_bot_token
POSTGRES_USER=smartx
POSTGRES_PASSWORD=smartx_pass
POSTGRES_DB=smartx_db
MONGO_URI=mongodb://mongo:27017
REDIS_URL=redis://redis:6379/0
MINIO_ACCESS_KEY=minio_access_key
MINIO_SECRET_KEY=minio_secret_key


---

🐳 Deployment with Docker

Start services

docker-compose build
docker-compose up -d

Run PostgreSQL migrations

docker-compose run --rm bot alembic upgrade head

Check logs

docker-compose logs -f bot


---

🛢 Database

MongoDB

Used for user profiles, messages, bot states.

PostgreSQL

Used for payments, subscriptions, audit logs.
Migrations are managed with Alembic.

Create new migration:

docker-compose run --rm bot alembic revision --autogenerate -m "new changes"
docker-compose run --rm bot alembic upgrade head


---

📊 Monitoring & Metrics

Prometheus enabled if PROMETHEUS_ENABLED=true in .env

Endpoint available at:


http://localhost:8081/metrics


---

🧑‍💻 Development (Local without Docker)

1. Create virtualenv



python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

2. Run bot



python bot.py

3. Run webhook server



uvicorn webhook.server:app --host 0.0.0.0 --port 8080


---

🔧 Services

Celery Worker


docker-compose run --rm worker

Admin API


http://localhost:8081

MinIO Dashboard


http://localhost:9000


---

🌍 Deployment on Cloud

1. Push code to GitHub/GitLab


2. Setup VPS/Cloud (AWS, GCP, Hetzner, DigitalOcean, etc.)


3. Install Docker + Compose


4. Pull repo and run:



docker-compose up -d

5. Use NGINX + Certbot for HTTPS on webhook & admin API.




---

👨‍💻 Authors

Akshay Verma
Telegram: @akshayverma0212



---

📜 License

MIT License
