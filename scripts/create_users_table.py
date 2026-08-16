"""
Create the users table in Neon PostgreSQL.
Run this once after adding the User model to db/models.py.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.connection import Base, engine
from src.db.models import User  # noqa: F401 — import triggers table registration

print("Creating users table in Neon PostgreSQL...")
try:
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("✅ users table created successfully (or already exists).")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)
