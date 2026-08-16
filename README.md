# SurakshaAI

AI-powered rural financial safety system for detecting fraud in SMS, WhatsApp-style text, emails, URLs, and UPI requests.

## Kaggle Training Flow

```bash
pip install -r requirements.txt
python scripts/prepare_kaggle_data.py
python scripts/train_ml.py
python scripts/train_url_upi.py
python scripts/train_transformer_kaggle.py --model distilbert --epochs 3
```

Processed data is written to `data/processed/`. Model artifacts are written to `models_store/`. Reports and metrics are written to `reports/`.

## API

```bash
uvicorn src.api.main:app --reload
```

Health check: `http://localhost:8000/api/v1/health`
