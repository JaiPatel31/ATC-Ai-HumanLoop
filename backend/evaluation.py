"""
ATC Parser Evaluation / Visualization
---------------------------------------
If metadata labels exist: compute accuracy.
If not: run parser across transcripts and show distributions.
"""

from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Iterable, Mapping, MutableMapping

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datasets import load_dataset
from parser import parse_atc


@dataclass(frozen=True)
class Sample:
    transcript: str
    expected: Mapping[str, object] | None = None


# --------------------
# Load dataset
# --------------------
def load_hf_samples(limit: int | None = 100) -> list[Sample]:
    ds = load_dataset("jacktol/ATC-ASR-Dataset", split="test")

    # remove audio to avoid decoding
    if "audio" in ds.column_names:
        ds = ds.remove_columns("audio")

    subset = ds.select(range(min(limit, len(ds))))
    samples = []

    for row in subset:
        transcript = row.get("text") or row.get("transcript") or ""
        # No metadata present — placeholder expected=None
        samples.append(Sample(transcript=transcript, expected=None))
    return samples


# --------------------
# Evaluation
# --------------------
def evaluate(samples: Iterable[Sample]) -> pd.DataFrame:
    records = []
    for s in samples:
        parsed = parse_atc(s.transcript)
        record = {"transcript": s.transcript}
        record.update(parsed)
        records.append(record)
    return pd.DataFrame(records)


# --------------------
# Visualization
# --------------------
def visualize(df: pd.DataFrame):
    print("\n=== Parsed field coverage ===")
    print(df.notna().sum())

    # Bar: how often each command/speaker appears
    cat_fields = ["command", "speaker", "callsign"]
    for field in cat_fields:
        if field in df.columns:
            plt.figure(figsize=(7, 4))
            sns.countplot(y=field, data=df, order=df[field].value_counts().index, palette="mako")
            plt.title(f"Distribution of parsed {field}")
            plt.tight_layout()
            plt.show()

    # Numeric fields
    for field in ["heading", "flight_level"]:
        if field in df.columns:
            plt.figure(figsize=(7, 4))
            sns.histplot(df[field].dropna(), kde=True, bins=20, color="skyblue")
            plt.title(f"Distribution of {field}")
            plt.xlabel(field)
            plt.tight_layout()
            plt.show()


# --------------------
# Entry point
# --------------------
if __name__ == "__main__":
    print("Loading jacktol/ATC-ASR-Dataset ...")
    samples = load_hf_samples(limit=200)
    print(f"Loaded {len(samples)} samples.")

    df = evaluate(samples)
    print(df.head())

    visualize(df)

    df.to_csv("parser_outputs.csv", index=False)
    print("\nSaved parser outputs to parser_outputs.csv")
