from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

# ایجاد engine با تست اتصال اتوماتیک
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,          # اگر connection قطع شده باشد، دوباره وصل می‌شود
    pool_size=10,
    max_overflow=20
)

# ساخت SessionLocal
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    """
    Dependency برای FastAPI: در هر درخواست یک session بده و بعد ببند.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection():
    """
    تست اتصال دیتابیس برای health-check
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
