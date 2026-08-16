"""
SurakshaAI — Database Package
==============================
Exposes the database engine, session factory, and Base
for use across the application.

Usage:
    from src.db import get_db, Base, engine
"""

from src.db.connection import Base, engine, get_db, SessionLocal

__all__ = ["Base", "engine", "get_db", "SessionLocal"]