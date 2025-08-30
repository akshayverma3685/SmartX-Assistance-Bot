#!/bin/bash
set -e  # agar koi error aaye to turant stop ho jaye

echo "🚀 SmartX Bot Deployment Started..."

# 1. Naya code repo se le aao
echo "📥 Pulling latest code from Git..."
git pull origin main

# 2. Docker images rebuild karo (sirf agar dependency badli ho to rebuild hoga)
echo "🐳 Building docker images..."
docker-compose build

# 3. Containers ko recreate aur run karo
echo "🔄 Restarting containers..."
docker-compose up -d

# 4. Status dikhao
echo "✅ Deployment complete! Current status:"
docker-compose ps
