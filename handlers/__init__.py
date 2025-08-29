"""
Handlers Package Initializer

Yeh file saare handlers ko import aur expose karti hai taaki
bot.py ya kisi bhi core module me easily use ho sake.

Example:
    from handlers import start_handler, admin_handler
"""

from . import (
    start,
    admin,
    ai,
    business,
    downloader,
    entertainment,
    menu,
    premium,
    profile,
    services,
    tools,
)

# Har handler ko explicit alias ke saath export kar dete hain
start_handler = start
admin_handler = admin
ai_handler = ai
business_handler = business
downloader_handler = downloader
entertainment_handler = entertainment
menu_handler = menu
premium_handler = premium
profile_handler = profile
services_handler = services
tools_handler = tools

__all__ = [
    "start_handler",
    "admin_handler",
    "ai_handler",
    "business_handler",
    "downloader_handler",
    "entertainment_handler",
    "menu_handler",
    "premium_handler",
    "profile_handler",
    "services_handler",
    "tools_handler",
]
