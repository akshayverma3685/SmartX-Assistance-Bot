🤖 SmartX Assistance Bot

"Your All-in-One AI + Productivity Telegram Assistant"

✨ Overview
SmartX Assistance is an all-in-one Telegram Bot offering AI, utilities, downloaders, news, weather, fun, and business tools.
It includes a Free & Premium plan plus an Admin Panel for monitoring and premium management.

🚀 Features

🟢 Free Features (Default Users)

🧠 AI Chat → 10 messages/day

📄 Document Summarizer → 2 files/day

🖼 AI Image → 3 images/day (low-res)

📥 Downloader → YouTube/Instagram Basic (720p, watermark)

📝 Tools → Notes, To-Do, QR Generator, Shortener (limited use)

🌦 Weather & News → Daily once

🎉 Entertainment → Unlimited games & fun commands

⭐ Free Trial: 3 Days Premium For New Users 

---

💎 Premium Features

🧠 AI Chat → Unlimited (Fast responses, Custom AI personalities)

📄 Summarizer → Unlimited files/month

🖼 AI Image → Unlimited (HD/4K)

🎙 Text ↔ Voice → Unlimited (voice customization in Ultra)

📥 Downloader → Unlimited 4K YouTube, TikTok, Music (Spotify/Apple)

📝 Tools → All unlocked (Currency, Crypto, Business calculators)

🌦 Weather & News → Unlimited + Auto daily push

💼 Business Tools → Invoice Generator, Expense Tracker, CRM (contacts save)

🎉 Entertainment → Exclusive memes/games + Owner Exclusive Content

🎖 Special Badge (Ultra Members only)

🎯 Early Access to new features

---

👑 Owner/Admin Features

📊 Admin Panel (Manage Users, Premium, Stats, Logs)

💳 Payments (Razorpay + Manual Activation System)

📢 Broadcast Messages to all users

🔒 Monitor API usage, errors, payments

🔗 Owner’s Social Links section (Follow/Connect CTA)

---

🏗️ Tech Stack

Language: Python 3.11+

Framework: Aiogram (Telegram Bot API)

Database: PostgreSQL / MongoDB

Payments: Razorpay API + Manual Mode

APIs: OpenAI, Weather, NewsAPI, Crypto, Downloaders

Deployment: Docker + Railway/Heroku/VPS

---

📂 Folder Structure

SmartX-Assistance-Bot
│── README.md
│── requirements.txt
│── config.py
│── bot.py      
├── core/
│   ├── handler
│   ├── services/ 
│   ├── payments/
│   ├── database/    
│   └── utils/   
├── admin/
│   ├── panel.py 
│   ├── broadcast.py
│   └── stats.py
│
├── user/
│   ├── onboarding.py  
│   ├── premium.py
│   └── profile.py
│
├── assets/
│   ├── logo.png
│   ├── icons/
│   └── themes/
│
└── docs/
    ├── DB_SCHEMA.md
    ├── API_DOCS.md
    └── ARCHITECTURE.md


---

⚙️ Installation Guide

🔹 1. Clone Repo

git clone https://github.com/akshayverma3685/SmartX-Assistance.git
cd SmartX-Assistance

🔹 2. Install Dependencies

pip install -r requirements.txt

🔹 3. Set Environment Variables

Create .env file:

BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:password@localhost:5432/smartx
RAZORPAY_KEY=your_razorpay_key
RAZORPAY_SECRET=your_razorpay_secret
OPENAI_KEY=your_openai_api_key
NEWS_API_KEY=your_newsapi_key
WEATHER_API_KEY=your_weatherapi_key

🔹 4. Run Bot

python bot.py

---

🌍 Deployment

Docker:

docker build -t smartx-assistance .
docker run -d --env-file .env smartx-assistance

Deploy on Railway / Heroku / VPS

---

🔐 License

MIT License – Free for personal & commercial use with attribution.

