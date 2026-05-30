import os
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def get_connection():
    try:
        import psycopg2
    except ImportError:
        raise RuntimeError("psycopg2 no disponible.")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
