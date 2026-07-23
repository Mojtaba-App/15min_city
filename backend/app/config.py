from pathlib import Path
import os
from dotenv import load_dotenv

# مسیر پوشه backend/
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

# لود فایل .env
load_dotenv(ENV_FILE)

# خواندن مقادیر
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# ساخت آدرس دیتابیس
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Debug برای تست (اختیاری – بعداً می‌توانی برداری)
print(">>> Database config loaded:")
print(" DB_HOST =", DB_HOST)
print(" DB_PORT =", DB_PORT)
print(" DB_NAME =", DB_NAME)
print(" DB_USER =", DB_USER)
print(" DB_PASSWORD loaded =", bool(DB_PASSWORD))
