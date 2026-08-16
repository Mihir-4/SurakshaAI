"""Initialize tables in Neon PostgreSQL database."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.db.connection import check_db, init_db


def main() -> None:
    print("Checking connection to Neon PostgreSQL...")
    if not check_db():
        print("❌ Could not connect to PostgreSQL. Check your DATABASE_URL in .env")
        sys.exit(1)
    
    print("Connected successfully! Creating all database tables...")
    init_db()
    print("✅ Database tables initialized successfully in Neon PostgreSQL!")


if __name__ == "__main__":
    main()
