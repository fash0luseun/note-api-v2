"""
migrate.py — Database Migration Runner
========================================
Reads SQL migration files from the /migrations folder,
executes them in order, and tracks which ones have been applied.

Usage:
    python migrate.py          # Apply all pending migrations
    python migrate.py --status # Show migration status
    python migrate.py --down   # Rollback instructions
"""

import os
import sys
from database import get_connection

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def ensure_tracking_table():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_applied_migrations() -> set:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT filename FROM schema_migrations")
        return {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()


def extract_up_sql(filepath: str) -> str:
    with open(filepath, "r") as f:
        content = f.read()

    if "-- ============ UP ============" in content:
        up_section = content.split("-- ============ UP ============")[1]
        if "-- ============ DOWN ============" in up_section:
            up_section = up_section.split("-- ============ DOWN ============")[0]
        return up_section.strip()

    return content


def run_migrations():
    ensure_tracking_table()
    applied = get_applied_migrations()

    migration_files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")
    )

    pending = [f for f in migration_files if f not in applied]

    if not pending:
        print("All migrations are up to date. Nothing to apply.")
        return

    conn = get_connection()
    try:
        cursor = conn.cursor()
        for filename in pending:
            filepath = os.path.join(MIGRATIONS_DIR, filename)
            up_sql = extract_up_sql(filepath)

            print(f"Applying: {filename}...")

            cleaned_lines = []
            for line in up_sql.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("--"):
                    cleaned_lines.append(line)
            cleaned_sql = "\n".join(cleaned_lines)

            for statement in cleaned_sql.split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)

            cursor.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)",
                (filename,),
            )
            conn.commit()
            print(f"   Applied: {filename}")

        print(f"\nSuccessfully applied {len(pending)} migration(s).")

    except Exception as e:
        conn.rollback()
        print(f"   Failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


def show_status():
    ensure_tracking_table()
    applied = get_applied_migrations()

    migration_files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")
    )

    print("\nMigration Status:")
    print("-" * 50)
    for f in migration_files:
        status = "Applied" if f in applied else "Pending"
        print(f"  {status}  {f}")
    print("-" * 50)


if __name__ == "__main__":
    if "--status" in sys.argv:
        show_status()
    elif "--down" in sys.argv:
        print("To rollback, manually run the DOWN section of the latest migration.")
        show_status()
    else:
        run_migrations()
        show_status()
