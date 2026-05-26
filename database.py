import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/notesdb")


def get_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def query(sql: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    conn = get_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql, params)

        if fetch_one:
            row = cursor.fetchone()
            conn.commit()
            return dict(row) if row else None
        elif fetch_all:
            rows = cursor.fetchall()
            conn.commit()
            return [dict(row) for row in rows]
        else:
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else None
    finally:
        conn.close()
