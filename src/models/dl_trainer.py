"""Kaggle-friendly deep learning trainer for transformer text models."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

from datasets import Dataset
from src.config import settings


MODEL_ALIASES = {
    "distilbert": "distilbert-base-uncased",
    "mbert": "bert-base-multilingual-cased",
    "indicbert": "ai4bharat/indic-bert",
}


@dataclass
class DLTrainConfig:
    model_alias: str = "distilbert"
    output_dir: str = "./models_store/dl/distilbert"
    max_length: int = 192
    learning_rate: float = 2e-5
    batch_size: int = 16
    epochs: int = 3
    save_checkpoints: bool = False


def compute_metrics(eval_pred) -> dict:
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary", zero_division=0
    )
    return {
        "f1_macro": f1_score(labels, preds, average="macro", zero_division=0),
        "fraud_precision": precision,
        "fraud_recall": recall,
        "fraud_f1": f1,
    }


def train_transformer(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    config: DLTrainConfig,
) -> Trainer:
    model_name = MODEL_ALIASES.get(config.model_alias, config.model_alias)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=config.max_length)

    train_ds = Dataset.from_pandas(
        pd.DataFrame({"text": train_df["cleaned_text"], "label": train_df["label_binary"].astype(int)})
    ).map(tokenize, batched=True)
    val_ds = Dataset.from_pandas(
        pd.DataFrame({"text": val_df["cleaned_text"], "label": val_df["label_binary"].astype(int)})
    ).map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
    training_kwargs = {
        "output_dir": config.output_dir,
        "learning_rate": config.learning_rate,
        "per_device_train_batch_size": config.batch_size,
        "per_device_eval_batch_size": config.batch_size,
        "num_train_epochs": config.epochs,
        "save_strategy": "epoch" if config.save_checkpoints else "no",
        "load_best_model_at_end": bool(config.save_checkpoints),
        "fp16": torch.cuda.is_available(),
        "report_to": [],
        "logging_strategy": "epoch",
        "seed": settings.RANDOM_SEED,
    }
    if config.save_checkpoints:
        training_kwargs["metric_for_best_model"] = "f1_macro"
        training_kwargs["greater_is_better"] = True
        training_kwargs["save_total_limit"] = 1
    argument_names = inspect.signature(TrainingArguments.__init__).parameters
    if "evaluation_strategy" in argument_names:
        training_kwargs["evaluation_strategy"] = "epoch"
    else:
        training_kwargs["eval_strategy"] = "epoch"

    args = TrainingArguments(**training_kwargs)
    trainer_kwargs = {
        "model": model,
        "args": args,
        "train_dataset": train_ds,
        "eval_dataset": val_ds,
        "data_collator": DataCollatorWithPadding(tokenizer),
        "compute_metrics": compute_metrics,
    }
    trainer_argument_names = inspect.signature(Trainer.__init__).parameters
    if "tokenizer" in trainer_argument_names:
        trainer_kwargs["tokenizer"] = tokenizer
    elif "processing_class" in trainer_argument_names:
        trainer_kwargs["processing_class"] = tokenizer

    trainer = Trainer(**trainer_kwargs)
    trainer.train()
    trainer.save_model(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)
    return trainer
