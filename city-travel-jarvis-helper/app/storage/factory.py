from functools import lru_cache
from app.settings import settings
from app.storage.google_sheets import GoogleSheetsStorage
from app.storage.memory import MemoryStorage
from app.seed import memory_seed
@lru_cache(maxsize=1)
def get_storage():
    return GoogleSheetsStorage() if settings.storage_mode == "google_sheets" else MemoryStorage(memory_seed())
