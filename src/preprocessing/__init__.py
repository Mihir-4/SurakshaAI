"""
SurakshaAI — Preprocessing Package
=====================================
Data cleaning, feature engineering, label mapping,
text augmentation, and train/val/test splitting.

Submodules:
  - text_cleaner      : HTML removal, Unicode normalization,
                        financial entity tokenization
  - feature_engineer  : hand-crafted feature extraction
  - label_mapper      : standardize labels to safe / fraud / unknown
  - augmentor         : training-split-only text augmentation
  - splitter          : stratified grouped train/val/test split
"""

from src.preprocessing.label_mapper import LabelMapper
from src.preprocessing.text_cleaner import TextCleaner
from src.preprocessing.feature_engineer import FeatureEngineer
from src.preprocessing.splitter import DataSplitter

__all__ = [
    "LabelMapper",
    "TextCleaner",
    "FeatureEngineer",
    "DataSplitter",
]