"""
SurakshaAI — AI-Powered Rural Financial Safety System
=====================================================
src package root.

All subpackages:
  - config      : centralised settings
  - data        : dataset download, validation, cataloging
  - db          : database connection and schema
  - preprocessing: text cleaning, feature engineering,
                   augmentation, splitting, label mapping
  - models      : ML and DL model training and registry
  - nlp         : language detection, translation, embeddings
  - engine      : rule engine, calibration, risk scoring,
                  fraud detection engine
  - llm         : Mistral prompt building, API client,
                  response parsing
  - api         : FastAPI application, routes, schemas
"""

__version__ = "1.0.0"
__author__  = "SurakshaAI Team"