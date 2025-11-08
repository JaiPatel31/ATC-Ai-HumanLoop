"""
AI-Enhanced Parser Evaluation
------------------------------
Re-evaluate the validation set using the AI-enhanced parser
to demonstrate improvements.
"""

import matplotlib
matplotlib.use('Agg')

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datasets import load_dataset
from parser_ai_enhanced import parse_atc_enhanced
from parser import parse_atc
from tqdm import tqdm

# Set up plotting
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'


def load_validation_transcripts(limit=100):
    """Load validation split transcripts."""
    print(f"\nLoading validation split transcripts (limit={limit})...")
    ds = load_dataset("jacktol/ATC-ASR-Dataset", split="validation")
    ds = ds.remove_columns(['audio'])
    if limit and limit < len(ds):
        ds = ds.select(range(limit))
    transcripts = [sample["text"] for sample in ds]
    print(f"✓ Loaded {len(transcripts)} validation transcripts")
    return transcripts


def compare_parsers_on_dataset(transcripts):
    """Evaluate both original and AI-enhanced parsers."""
    print("\nEvaluating both parsers...")

    original_results = []
    enhanced_results = []

    for idx, transcript in enumerate(tqdm(transcripts, desc="Parsing transcripts")):
        try:
            # Parse with both
            original = parse_atc(transcript)
            enhanced = parse_atc_enhanced(transcript)

            original_results.append({
                "sample_id": idx,
                "transcript": transcript,
                "callsign": original.get("callsign"),
                "heading": original.get("heading"),
                "flight_level": original.get("flight_level"),
                "command": original.get("command"),
                "speaker": original.get("speaker"),
            })

            enhanced_results.append({
                "sample_id": idx,
                "transcript": transcript,
                "callsign": enhanced.get("callsign"),
                "heading": enhanced.get("heading"),
                "flight_level": enhanced.get("flight_level"),
                "command": enhanced.get("command"),
                "speaker": enhanced.get("speaker"),
                "message_type": enhanced.get("message_type"),
                "airline": enhanced.get("airline"),
            })

        except Exception as e:
            print(f"\n⚠️  Error on sample {idx}: {e}")
            continue

    df_original = pd.DataFrame(original_results)
    df_enhanced = pd.DataFrame(enhanced_results)

    print(f"\n✓ Parsed {len(df_original)} samples with both parsers")

    return df_original, df_enhanced


def analyze_improvements(df_original, df_enhanced):
    """Analyze and visualize improvements."""
    output_path = Path("evaluation_results")
    output_path.mkdir(exist_ok=True)

    print("\n" + "="*70)
    print("AI-ENHANCED PARSER IMPROVEMENTS")
    print("="*70)

    total = len(df_original)

    # Compare field extraction rates
    print("\n📊 Field Extraction Rate Comparison:")
    print("="*70)

    fields = ['callsign', 'heading', 'flight_level', 'command', 'speaker']

    original_rates = {}
    enhanced_rates = {}
    improvements = {}

    for field in fields:
        orig_count = df_original[field].notna().sum()
        enh_count = df_enhanced[field].notna().sum()

        orig_rate = orig_count / total * 100
        enh_rate = enh_count / total * 100
        improvement = enh_rate - orig_rate

        original_rates[field] = orig_rate
        enhanced_rates[field] = enh_rate
        improvements[field] = improvement

        symbol = "📈" if improvement > 0 else "📉" if improvement < 0 else "="
        print(f"\n{field.upper()}:")
        print(f"  Original:  {orig_rate:5.1f}% ({orig_count}/{total})")
        print(f"  Enhanced:  {enh_rate:5.1f}% ({enh_count}/{total})")
        print(f"  {symbol} Change:   {improvement:+5.1f}%")

    # Visualize comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # Left: Side-by-side comparison
    x = range(len(fields))
    width = 0.35

    bars1 = ax1.bar([i - width/2 for i in x], [original_rates[f] for f in fields],
                    width, label='Original Parser', color='lightcoral',
                    edgecolor='black', alpha=0.8)
    bars2 = ax1.bar([i + width/2 for i in x], [enhanced_rates[f] for f in fields],
                    width, label='AI-Enhanced Parser', color='lightgreen',
                    edgecolor='black', alpha=0.8)

    ax1.set_xlabel('Field', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Extraction Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Parser Comparison: Original vs AI-Enhanced',
                  fontsize=14, fontweight='bold', pad=15)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f.replace('_', '\n') for f in fields])
    ax1.legend(fontsize=11)
    ax1.set_ylim(0, 105)
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{height:.0f}%', ha='center', va='bottom',
                    fontsize=9, fontweight='bold')

    # Right: Improvement delta
    colors_delta = ['green' if improvements[f] > 0 else 'red' if improvements[f] < 0 else 'gray'
                    for f in fields]
    bars_delta = ax2.barh(fields, [improvements[f] for f in fields],
                          color=colors_delta, edgecolor='black', alpha=0.7)

    ax2.set_xlabel('Improvement (%)', fontsize=12, fontweight='bold')
    ax2.set_title('AI Enhancement Impact\n(Positive = Better)',
                  fontsize=14, fontweight='bold', pad=15)
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=1)
    ax2.grid(axis='x', alpha=0.3)

    # Add value labels
    for bar, field in zip(bars_delta, fields):
        width = bar.get_width()
        label_x = width + (1 if width > 0 else -1)
        ax2.text(label_x, bar.get_y() + bar.get_height()/2,
                f'{width:+.1f}%', ha='left' if width > 0 else 'right',
                va='center', fontweight='bold', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path / 'parser_comparison.png')
    print(f"\n✓ Saved: parser_comparison.png")
    plt.close()

    # Analyze specific improvements
    print("\n🔍 Detailed Improvement Analysis:")
    print("="*70)

    # Callsign improvements
    callsign_fixes = 0
    for idx in range(len(df_original)):
        orig_cs = df_original.iloc[idx]['callsign']
        enh_cs = df_enhanced.iloc[idx]['callsign']

        # Count as improvement if:
        # 1. Enhanced found one but original didn't
        # 2. Enhanced is shorter (likely removed extra words)
        if pd.notna(enh_cs):
            if pd.isna(orig_cs):
                callsign_fixes += 1
            elif len(str(enh_cs)) < len(str(orig_cs)):
                callsign_fixes += 1

    print(f"\nCallsign Extraction Improvements:")
    print(f"  Fixed/improved: {callsign_fixes} samples")
    print(f"  Examples of fixes:")

    # Show some examples
    examples_shown = 0
    for idx in range(len(df_original)):
        if examples_shown >= 5:
            break
        orig_cs = df_original.iloc[idx]['callsign']
        enh_cs = df_enhanced.iloc[idx]['callsign']

        if pd.notna(orig_cs) and pd.notna(enh_cs) and orig_cs != enh_cs:
            transcript = df_original.iloc[idx]['transcript'][:60]
            print(f"    \"{transcript}...\"")
            print(f"      Original: {orig_cs}")
            print(f"      Enhanced: {enh_cs} ✓")
            examples_shown += 1

    # Flight level fixes
    fl_fixes = 0
    for idx in range(len(df_original)):
        orig_fl = df_original.iloc[idx]['flight_level']
        enh_fl = df_enhanced.iloc[idx]['flight_level']

        # Fix if enhanced corrected an invalid flight level
        if pd.notna(orig_fl) and pd.notna(enh_fl):
            if orig_fl > 600 and enh_fl <= 600:
                fl_fixes += 1

    if fl_fixes > 0:
        print(f"\nFlight Level Fixes:")
        print(f"  Corrected invalid levels: {fl_fixes} samples")

    # Message type distribution
    if 'message_type' in df_enhanced.columns:
        print(f"\n📋 Message Type Distribution (AI-Enhanced Parser):")
        msg_types = df_enhanced['message_type'].value_counts()
        for msg_type, count in msg_types.items():
            print(f"  {msg_type:15s}: {count:3d} ({count/total*100:5.1f}%)")

    # Overall summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    total_improvements = sum(1 for v in improvements.values() if v > 0)
    total_degradations = sum(1 for v in improvements.values() if v < 0)

    print(f"\nFields improved:     {total_improvements}/{len(fields)}")
    print(f"Fields degraded:     {total_degradations}/{len(fields)}")
    print(f"Callsign fixes:      {callsign_fixes}")

    avg_improvement = sum(improvements.values()) / len(improvements)
    print(f"\nAverage improvement: {avg_improvement:+.2f}%")

    if avg_improvement > 0:
        print("\n✅ AI-Enhanced Parser shows OVERALL IMPROVEMENT!")
    else:
        print("\n⚠️  Mixed results - some improvements, some regressions")

    print("="*70)

    return improvements


def main():
    """Main evaluation pipeline."""
    print("="*70)
    print("AI-ENHANCED PARSER EVALUATION")
    print("="*70)

    # Load data
    transcripts = load_validation_transcripts(limit=100)

    # Compare parsers
    df_original, df_enhanced = compare_parsers_on_dataset(transcripts)

    # Save results
    df_original.to_csv("original_parser_results.csv", index=False)
    df_enhanced.to_csv("enhanced_parser_results.csv", index=False)
    print(f"\n✓ Saved comparison results to CSV files")

    # Analyze improvements
    improvements = analyze_improvements(df_original, df_enhanced)

    print("\n✅ Evaluation complete!")
    print("="*70)


if __name__ == "__main__":
    main()

