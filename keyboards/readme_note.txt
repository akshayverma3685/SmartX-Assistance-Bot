Place all keyboard modules under keyboards/.
Use functions like main_menu_kb(lang_strings) to get language-aware labels.
Handlers should import like:
from keyboards import main_menu_kb, downloader_menu_kb
