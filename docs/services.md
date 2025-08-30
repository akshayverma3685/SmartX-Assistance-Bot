# 🔧 Services

Service layer provides reusable modules.

## Available Services
- **image_service.py** → AI image generation
- **news_service.py** → Fetch latest news
- **translation_service.py** → Translate text
- **payment_service.py** → Razorpay integration
- **speech_service.py** → Text-to-speech & speech-to-text
- **weather_service.py** → Weather API integration

---
Services follow a clean structure:
```python
class ServiceName:
    async def run(...):
        pass
