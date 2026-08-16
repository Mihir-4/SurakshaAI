# SurakshaAI Project Progress

## Project Description

SurakshaAI is a binary scam-detection system for financial communications. Its core question is simple:

> Is this input safe or is it a scam?

The system is designed for rural digital banking safety in India. It analyzes text messages, WhatsApp-style messages, emails, URLs, and UPI payment strings. The model output is binary at the classifier level:

- `safe`
- `fraud`

Risk levels such as low risk, caution, high risk, and very high risk are produced later by the risk engine from calibrated probabilities and rule-based evidence. They are not separate training classes.

## Current Dataset Status

Raw datasets are available under `data/raw/`:

- Financial scams dataset
- SMS phishing dataset
- SMS spam dataset
- Phishing email datasets
- Indian banking SMS dataset
- Malicious URL dataset
- Synthetic/manual banking, loan, WhatsApp, and UPI datasets

Processed text splits are available under `data/processed/`:

- `text_train.csv`
- `text_val.csv`
- `text_test.csv`

The current dataset is suitable for first-stage binary scam detection. It has strong phishing, smishing, spam, URL, and synthetic UPI coverage. The main limitation is that some India-specific financial scam categories, especially loan/UPI/WhatsApp patterns, still need a stronger gold benchmark for final claims.

## Completed Training

### Classical Text ML

Models trained:

- Logistic Regression
- Decision Tree
- Random Forest
- XGBoost Text

Best classical text model so far:

- `xgboost_text`

Observed test performance:

- Accuracy: about 96.98%
- Fraud recall: about 96.70%
- F1 macro: about 96.91%

### URL Model

URL model trained on malicious/benign URL features.

Observed performance:

- Accuracy: about 89.98%
- Fraud recall: about 82.08%
- ROC AUC: about 96.19%

This is usable for a first URL classifier, but URL feature engineering can still be improved.

### UPI Model

UPI model trained on synthetic UPI examples.

Observed performance:

- Accuracy: 100%
- Fraud recall: 100%

This proves the UPI pipeline works, but the synthetic dataset is too easy. These numbers should not be presented as real-world UPI robustness without a harder benchmark.

### Deep Learning

DistilBERT has been trained on Kaggle GPU.

Observed test performance after 10 epochs:

- Accuracy: about 97.60%
- F1 macro: about 97.55%
- Fraud precision: about 96.65%
- Fraud recall: about 97.74%
- ROC AUC: about 99.72%
- Fraud recall at 5% FPR: about 99.03%

mBERT and MuRIL are being trained for multilingual and Indian-language comparison.

MuRIL 3-epoch training completed successfully.

Observed MuRIL test performance:

- Accuracy: about 97.46%
- F1 macro: about 97.40%
- Fraud precision: about 96.79%
- Fraud recall: about 97.26%
- Fraud F1: about 97.03%
- ROC AUC: about 99.43%
- Fraud recall at 5% FPR: about 98.47%

MuRIL is close to DistilBERT and gives the project a defensible Indian-language/multilingual comparison model.

## Model Comparison Plan

Use `scripts/evaluate_all_models.py` after downloading all Kaggle-trained model folders into `models_store/dl/`.

Expected local folder layout:

```text
models_store/
  ml/
    best_text_ml.pkl
    xgboost_text.pkl
    random_forest.pkl
    logistic_regression.pkl
    decision_tree.pkl
    tfidf_vectorizer.pkl
    feature_scaler.pkl
    url_model.pkl
    upi_model.pkl
  dl/
    distilbert/
      final_model/
        config.json
        model.safetensors
        tokenizer files...
    mbert/
      final_model/
        config.json
        model.safetensors
        tokenizer files...
    muril/
      final_model/
        config.json
        model.safetensors
        tokenizer files...
```

Evaluation command:

```powershell
python scripts/evaluate_all_models.py
```

If running locally without GPU and DL evaluation is slow:

```powershell
python scripts/evaluate_all_models.py --max-dl-samples 500
```

If you only want classical ML, URL, and UPI:

```powershell
python scripts/evaluate_all_models.py --skip-dl
```

Outputs:

- `reports/all_model_comparison.csv`
- `reports/all_model_comparison.json`

## Model Selection Rules

For the final text DL model, choose by:

1. Highest fraud recall
2. Highest F1 macro
3. Highest fraud recall at 5% false positive rate
4. Faster/smaller model if metrics are close

Likely final setup:

- Best text ML: XGBoost Text
- Best text DL: DistilBERT, mBERT, or MuRIL winner
- URL model: URL feature classifier
- UPI model: UPI feature classifier
- Rule engine: handcrafted fraud signal layer

## Next Steps To Complete The Project

1. Use DistilBERT as the current final DL model unless a larger multilingual model finishes successfully.
2. If Kaggle output space allows, train either mBERT or MuRIL in low-output mode. Do not save per-epoch checkpoints.
3. Download each completed Kaggle model output locally into `models_store/dl/<model_name>/final_model/`.
4. Run `python scripts/evaluate_all_models.py`.
5. Select the best DL model using fraud recall, F1 macro, and fraud recall at 5% FPR.
6. Create a gold benchmark CSV with realistic Indian scam/safe examples that were not used in training.
7. Run final benchmark evaluation.
8. Wire the selected ML/DL models into the hybrid fraud engine.
9. Add final API endpoints and test with examples.
10. Build or finish the frontend demo.
11. Prepare final report: dataset audit, model comparison, architecture, screenshots, limitations, and future work.

## Kaggle Output-Space Decision

mBERT and MuRIL are much larger than DistilBERT. Saving checkpoints every epoch can exceed Kaggle output limits.

The Kaggle notebooks have been updated to low-output mode:

- `save_strategy = "no"`
- final model is saved only once at the end
- no per-epoch checkpoint folders are kept

Recommended training order now:

1. Keep DistilBERT result as the primary DL model.
2. Try MuRIL for 3 epochs if Indian-language comparison is needed.
3. Skip mBERT if output/runtime remains tight.

This is acceptable because the project already has a strong trained DL model. mBERT/MuRIL are comparison models, not blockers for completing the system.

## Current Project Position

The ML and DL model development phase is complete for the first full system version.

Selected models:

- Text DL: mBERT
- Text ML: XGBoost Text / `best_text_ml.pkl`
- URL ML: `url_model.pkl`
- UPI ML: `upi_model.pkl`

Selected model config:

- `models_store/selected_models.json`

The project is now moving from model training into:

- model comparison
- final model selection
- hybrid engine integration
- gold benchmark testing
- demo/API/frontend completion

## Gold Benchmark Workflow

Gold benchmark scripts have been added:

- `scripts/create_gold_benchmark.py`
- `scripts/evaluate_gold_benchmark.py`

Create the benchmark:

```powershell
python scripts/create_gold_benchmark.py
```

This writes:

```text
data/external/surakshaai_gold_test.csv
```

Evaluate the full hybrid engine:

```powershell
python scripts/evaluate_gold_benchmark.py
```

This writes:

```text
reports/gold_benchmark_predictions.csv
reports/gold_benchmark_metrics.json
reports/module8_final_evaluation.csv
```

Important: the generated gold benchmark is a starting benchmark. For final capstone reporting, review and edit it manually so it contains realistic, non-template examples in your own wording. Do not use it for training.
