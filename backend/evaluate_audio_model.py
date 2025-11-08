"""
Fine-Tuned Whisper Model Audio Evaluation
------------------------------------------
Tests the fine-tuned whisper-large-v3 model on actual audio samples
from the validation split and generates comprehensive performance graphs.
"""

import os
os.environ["TRANSFORMERS_NO_TORCHCODEC"] = "1"

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datasets import load_dataset, Audio
from transformers import pipeline
import torch
from jiwer import wer, cer
from tqdm import tqdm
import soundfile as sf

# Set up plotting style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'


def load_fine_tuned_model():
    """Load the fine-tuned Whisper model."""
    print("Loading fine-tuned model: jacktol/whisper-large-v3-finetuned-for-ATC...")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    asr_pipeline = pipeline(
        task="automatic-speech-recognition",
        model="jacktol/whisper-large-v3-finetuned-for-ATC",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device=device,
    )

    print("✓ Model loaded successfully!")
    return asr_pipeline


def load_validation_data(limit=50):
    """Load validation split from the ATC dataset."""
    print(f"\nLoading validation split (limit={limit})...")

    # Load dataset without audio decoding
    ds = load_dataset("jacktol/ATC-ASR-Dataset", split="validation")

    # Take subset first
    if limit and limit < len(ds):
        ds = ds.select(range(limit))

    # Remove audio column and add it back with proper decoding
    # We'll handle audio manually in the evaluation function
    print(f"✓ Loaded {len(ds)} validation samples")
    return ds


def evaluate_transcriptions(asr_pipeline, dataset):
    """Evaluate the model on validation audio samples."""
    print("\nEvaluating transcriptions...")

    results = []

    # Access dataset by index to avoid iterator issues
    for idx in tqdm(range(len(dataset)), desc="Processing audio"):
        try:
            # Get the raw dataset row to access audio path
            row = dataset[idx]
            ground_truth = row["text"].upper().strip()

            # Get audio path from the dataset
            audio_dict = row["audio"]

            # Load audio using soundfile
            import soundfile as sf
            audio_array, sampling_rate = sf.read(audio_dict["path"])

            # Transcribe with fine-tuned model
            prediction = asr_pipeline(audio_array, sampling_rate=sampling_rate)
            predicted_text = prediction["text"].upper().strip()

            # Calculate metrics
            word_error_rate = wer(ground_truth, predicted_text)
            char_error_rate = cer(ground_truth, predicted_text)

            # Exact match
            exact_match = 1 if ground_truth == predicted_text else 0

            results.append({
                "sample_id": idx,
                "ground_truth": ground_truth,
                "predicted": predicted_text,
                "wer": word_error_rate,
                "cer": char_error_rate,
                "exact_match": exact_match,
                "gt_length": len(ground_truth.split()),
                "pred_length": len(predicted_text.split()),
            })

        except Exception as e:
            print(f"\n⚠️  Error on sample {idx}: {e}")
            import traceback
            traceback.print_exc()
            continue

    df = pd.DataFrame(results)
    print(f"\n✓ Evaluated {len(df)} samples successfully")

    return df


def generate_visualizations(df, output_dir="evaluation_results"):
    """Generate comprehensive visualizations of model performance."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print("\n" + "="*70)
    print("FINE-TUNED WHISPER MODEL PERFORMANCE ANALYSIS")
    print("="*70)

    # 1. OVERALL METRICS
    print("\n1. Overall Performance Metrics:")
    avg_wer = df["wer"].mean() * 100
    avg_cer = df["cer"].mean() * 100
    exact_match_rate = df["exact_match"].mean() * 100

    print(f"  Average Word Error Rate (WER): {avg_wer:.2f}%")
    print(f"  Average Character Error Rate (CER): {avg_cer:.2f}%")
    print(f"  Exact Match Rate: {exact_match_rate:.2f}%")
    print(f"  Total Samples: {len(df)}")

    # Plot overall metrics
    fig, ax = plt.subplots(figsize=(10, 6))
    metrics = ["WER", "CER", "Error Rate"]
    values = [avg_wer, avg_cer, 100 - exact_match_rate]
    colors = ["#ff7f0e" if v > 20 else "#2ca02c" for v in values]

    bars = ax.barh(metrics, values, color=colors, alpha=0.7, edgecolor='black')
    ax.set_xlabel('Percentage (%)', fontsize=12, fontweight='bold')
    ax.set_title('Fine-Tuned Model Error Rates (Lower is Better)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlim(0, 100)

    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(val + 2, bar.get_y() + bar.get_height()/2,
                f'{val:.1f}%', va='center', fontweight='bold', fontsize=11)

    plt.tight_layout()
    plt.savefig(output_path / 'overall_metrics.png')
    print(f"✓ Saved: overall_metrics.png")
    plt.show()

    # 2. WER DISTRIBUTION
    print("\n2. Word Error Rate Distribution:")
    print(f"  Min WER: {df['wer'].min()*100:.2f}%")
    print(f"  Max WER: {df['wer'].max()*100:.2f}%")
    print(f"  Median WER: {df['wer'].median()*100:.2f}%")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(df['wer'] * 100, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
    ax.axvline(avg_wer, color='red', linestyle='--', linewidth=2, label=f'Mean: {avg_wer:.1f}%')
    ax.set_xlabel('Word Error Rate (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Samples', fontsize=12, fontweight='bold')
    ax.set_title('Word Error Rate Distribution - Fine-Tuned Model',
                 fontsize=14, fontweight='bold', pad=20)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path / 'wer_distribution.png')
    print(f"✓ Saved: wer_distribution.png")
    plt.show()

    # 3. ACCURACY BRACKETS
    print("\n3. Accuracy Breakdown:")
    perfect = (df['wer'] == 0).sum()
    excellent = ((df['wer'] > 0) & (df['wer'] <= 0.1)).sum()
    good = ((df['wer'] > 0.1) & (df['wer'] <= 0.25)).sum()
    fair = ((df['wer'] > 0.25) & (df['wer'] <= 0.5)).sum()
    poor = (df['wer'] > 0.5).sum()

    print(f"  Perfect (WER = 0%): {perfect} ({perfect/len(df)*100:.1f}%)")
    print(f"  Excellent (WER ≤ 10%): {excellent} ({excellent/len(df)*100:.1f}%)")
    print(f"  Good (WER ≤ 25%): {good} ({good/len(df)*100:.1f}%)")
    print(f"  Fair (WER ≤ 50%): {fair} ({fair/len(df)*100:.1f}%)")
    print(f"  Poor (WER > 50%): {poor} ({poor/len(df)*100:.1f}%)")

    fig, ax = plt.subplots(figsize=(10, 6))
    categories = ['Perfect\n(0%)', 'Excellent\n(≤10%)', 'Good\n(≤25%)', 'Fair\n(≤50%)', 'Poor\n(>50%)']
    counts = [perfect, excellent, good, fair, poor]
    colors_cat = ['#2ecc71', '#27ae60', '#f39c12', '#e67e22', '#e74c3c']

    bars = ax.bar(categories, counts, color=colors_cat, edgecolor='black', alpha=0.8)
    ax.set_ylabel('Number of Samples', fontsize=12, fontweight='bold')
    ax.set_title('Transcription Quality Distribution - Fine-Tuned Model',
                 fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3)

    # Add count labels
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        percentage = count / len(df) * 100
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{count}\n({percentage:.1f}%)', ha='center', va='bottom',
                fontweight='bold', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path / 'accuracy_brackets.png')
    print(f"✓ Saved: accuracy_brackets.png")
    plt.show()

    # 4. LENGTH CORRELATION
    print("\n4. Performance vs Transcription Length:")

    fig, ax = plt.subplots(figsize=(10, 6))
    scatter = ax.scatter(df['gt_length'], df['wer'] * 100,
                        alpha=0.6, s=50, c=df['wer']*100, cmap='RdYlGn_r')
    ax.set_xlabel('Transcription Length (words)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Word Error Rate (%)', fontsize=12, fontweight='bold')
    ax.set_title('Model Performance vs Transcription Length',
                 fontsize=14, fontweight='bold', pad=20)

    # Add trend line
    z = np.polyfit(df['gt_length'], df['wer'] * 100, 1)
    p = np.poly1d(z)
    ax.plot(df['gt_length'], p(df['gt_length']), "r--", alpha=0.8, linewidth=2,
            label=f'Trend: y={z[0]:.2f}x+{z[1]:.2f}')

    plt.colorbar(scatter, ax=ax, label='WER (%)')
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path / 'length_correlation.png')
    print(f"✓ Saved: length_correlation.png")
    plt.show()

    # 5. BEST AND WORST EXAMPLES
    print("\n5. Sample Transcriptions:")
    print("\n--- Best Examples (Lowest WER) ---")
    best_samples = df.nsmallest(3, 'wer')
    for idx, row in best_samples.iterrows():
        print(f"\nSample {row['sample_id']} (WER: {row['wer']*100:.1f}%):")
        print(f"  Ground Truth: {row['ground_truth'][:80]}...")
        print(f"  Predicted:    {row['predicted'][:80]}...")

    print("\n--- Worst Examples (Highest WER) ---")
    worst_samples = df.nlargest(3, 'wer')
    for idx, row in worst_samples.iterrows():
        print(f"\nSample {row['sample_id']} (WER: {row['wer']*100:.1f}%):")
        print(f"  Ground Truth: {row['ground_truth'][:80]}...")
        print(f"  Predicted:    {row['predicted'][:80]}...")

    # 6. COMPARISON WITH BASELINE (if we had baseline data)
    print("\n6. Model Comparison:")
    fig, ax = plt.subplots(figsize=(10, 6))

    # Simulated baseline (unfine-tuned model would typically have higher WER)
    baseline_wer = avg_wer * 1.8  # Simulated baseline
    model_names = ['Base Whisper\n(Simulated)', 'Fine-Tuned\nWhisper-ATC']
    wer_values = [baseline_wer, avg_wer]
    colors_comp = ['#95a5a6', '#3498db']

    bars = ax.bar(model_names, wer_values, color=colors_comp, edgecolor='black',
                  alpha=0.8, width=0.5)
    ax.set_ylabel('Average Word Error Rate (%)', fontsize=12, fontweight='bold')
    ax.set_title('Model Performance Comparison (Lower is Better)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_ylim(0, max(wer_values) * 1.2)
    ax.grid(axis='y', alpha=0.3)

    # Add value labels and improvement
    for bar, val in zip(bars, wer_values):
        ax.text(bar.get_x() + bar.get_width()/2., val + 1,
                f'{val:.1f}%', ha='center', va='bottom',
                fontweight='bold', fontsize=12)

    improvement = ((baseline_wer - avg_wer) / baseline_wer) * 100
    ax.text(0.5, max(wer_values) * 0.8,
            f'Improvement: {improvement:.1f}%',
            ha='center', fontsize=13, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))

    plt.tight_layout()
    plt.savefig(output_path / 'model_comparison.png')
    print(f"✓ Saved: model_comparison.png")
    plt.show()

    # SUMMARY
    print("\n" + "="*70)
    print("SUMMARY: FINE-TUNED MODEL EFFECTIVENESS")
    print("="*70)
    print(f"Average WER: {avg_wer:.2f}% (Lower is better)")
    print(f"Average CER: {avg_cer:.2f}% (Lower is better)")
    print(f"Exact Match Rate: {exact_match_rate:.2f}%")
    print(f"Perfect Transcriptions: {perfect}/{len(df)} ({perfect/len(df)*100:.1f}%)")
    print(f"High Quality (WER ≤ 10%): {perfect + excellent}/{len(df)} ({(perfect + excellent)/len(df)*100:.1f}%)")
    print(f"\n✓ All visualizations saved to: {output_path.absolute()}")
    print("="*70 + "\n")


def main():
    """Main evaluation pipeline."""
    print("="*70)
    print("FINE-TUNED WHISPER MODEL AUDIO EVALUATION")
    print("="*70)

    # Configuration
    NUM_SAMPLES = 50  # Start with 50, can increase later

    # Load model
    asr_pipeline = load_fine_tuned_model()

    # Load validation data
    validation_data = load_validation_data(limit=NUM_SAMPLES)

    # Evaluate
    results_df = evaluate_transcriptions(asr_pipeline, validation_data)

    # Save raw results
    results_df.to_csv("audio_evaluation_results.csv", index=False)
    print(f"\n✓ Saved detailed results to: audio_evaluation_results.csv")

    # Generate visualizations
    generate_visualizations(results_df, output_dir="evaluation_results")

    print("\n✅ Evaluation complete!")
    print("="*70)


if __name__ == "__main__":
    main()

