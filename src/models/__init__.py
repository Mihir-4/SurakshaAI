"""
SurakshaAI — Models Package
=============================
All model training, serving, and registry components.

Submodules:
  - ml_trainer     : classical ML models (LR, DT, RF, XGBoost)
  - dl_trainer     : deep learning models (BiLSTM, DistilBERT,
                     IndicBERT, mBERT)
  - url_model      : URL XGBoost classifier with feature extraction
  - upi_model      : UPI XGBoost classifier with feature extraction
  - model_registry : tracks model versions and production selection

Production components:
  - Best ML model  (selected in Module 3)
  - Best DL model  (selected in Module 4)
  - URL XGBoost    (trained in Module 3)
  - UPI XGBoost    (trained in Module 3)
"""

from src.models.model_registry import ArtifactRegistry, ModelCard

ModelRegistry = ArtifactRegistry

__all__ = ["ArtifactRegistry", "ModelCard", "ModelRegistry"]
