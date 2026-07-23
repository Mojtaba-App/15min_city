from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

# این‌ها را مستقیم مقداردهی کن تا مطمئن شوی مشکل از env نیست
DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("✅ اتصال دیتابیس برقرار شد!")
        result = conn.execute(text("SELECT count(*) FROM v_block_accessibility_15min")).scalar()
        print(f"✅ جدول/ویو پیدا شد! تعداد رکوردها: {result}")
except Exception as e:
    print(f"❌ خطا: {e}")
