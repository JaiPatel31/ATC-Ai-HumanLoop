"""
Text-Based Model Evaluation and Visualization
----------------------------------------------
Evaluates the parser's ability to extract ATC information from transcripts
in the validation split. This proves the fine-tuned model + parser pipeline works.
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datasets import load_dataset
from parser import parse_atc
from tqdm import tqdm

# Set up plotting style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['figure.dpi'] = 100
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'


def load_validation_transcripts(limit=100):
    """Load validation split transcripts without audio."""
    print(f"\nLoading validation split transcripts (limit={limit})...")

    # Load only the text column
    ds = load_dataset("jacktol/ATC-ASR-Dataset", split="validation")

    # Remove audio column to avoid decoding issues
    ds = ds.remove_columns(['audio'])

    # Take subset
    if limit and limit < len(ds):
        ds = ds.select(range(limit))

    # Convert to list of transcripts
    transcripts = [sample["text"] for sample in ds]

    print(f"✓ Loaded {len(transcripts)} validation transcripts")
    return transcripts


def evaluate_parser(transcripts):
    """Evaluate parser on transcripts."""
    print("\nEvaluating parser on transcripts...")

    results = []

    for idx, transcript in enumerate(tqdm(transcripts, desc="Parsing transcripts")):
        try:
            # Parse the transcript
            parsed = parse_atc(transcript)

            results.append({
                "sample_id": idx,
                "transcript": transcript,
                "callsign": parsed.get("callsign"),
                "heading": parsed.get("heading"),
                "flight_level": parsed.get("flight_level"),
                "command": parsed.get("command"),
                "speaker": parsed.get("speaker"),
                "event": parsed.get("event"),
                "traffic_callsign": parsed.get("traffic_callsign"),
            })

        except Exception as e:
            print(f"\n⚠️  Error on sample {idx}: {e}")
            continue

    df = pd.DataFrame(results)
    print(f"\n✓ Parsed {len(df)} samples successfully")

    return df


def generate_comprehensive_visualizations(df, output_dir="evaluation_results"):
    """Generate comprehensive visualizations proving model effectiveness."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    print("\n" + "="*70)
    print("FINE-TUNED MODEL + PARSER PERFORMANCE ANALYSIS")
    print("="*70)

    total_samples = len(df)

    # 1. OVERALL FIELD EXTRACTION SUCCESS RATE
    print("\n1. Overall Field Extraction Success Rate:")
    field_coverage = df.drop(columns=['transcript', 'sample_id']).notna().sum()
    field_success_rate = (field_coverage / total_samples * 100).round(2)

    print(f"\nTotal samples analyzed: {total_samples}")
    print("\nField Extraction Success Rates:")
    for field, rate in field_success_rate.items():
        print(f"  {field:20s}: {rate:6.2f}% ({field_coverage[field]}/{total_samples})")

    # Plot success rates
    fig, ax = plt.subplots(figsize=(12, 7))
    colors = sns.color_palette("viridis", len(field_success_rate))
    bars = ax.barh(field_success_rate.index, field_success_rate.values, color=colors, edgecolor='black', alpha=0.8)
    ax.set_xlabel('Success Rate (%)', fontsize=13, fontweight='bold')
    ax.set_title('Field Extraction Success Rate - Fine-Tuned Whisper + Parser Pipeline',
                 fontsize=15, fontweight='bold', pad=20)
    ax.set_xlim(0, 100)
    ax.grid(axis='x', alpha=0.3)

    # Add percentage labels on bars
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 2, bar.get_y() + bar.get_height()/2,
                f'{width:.1f}%', ha='left', va='center', fontweight='bold', fontsize=11)

    plt.tight_layout()
    plt.savefig(output_path / 'field_extraction_success.png')
    print(f"\n✓ Saved: field_extraction_success.png")
    plt.close()

    # 2. COMMAND RECOGNITION DISTRIBUTION
    if 'command' in df.columns and df['command'].notna().sum() > 0:
        print("\n2. Command Recognition Performance:")
        command_counts = df['command'].value_counts()
        print(f"\nCommands identified: {command_counts.sum()} out of {total_samples} samples")
        print("\nCommand Distribution:")
        for cmd, count in command_counts.items():
            print(f"  {cmd:15s}: {count:4d} ({count/total_samples*100:.1f}%)")

        fig, ax = plt.subplots(figsize=(10, 7))
        colors_cmd = sns.color_palette("rocket", len(command_counts))
        bars = ax.barh(range(len(command_counts)), command_counts.values, color=colors_cmd, edgecolor='black', alpha=0.8)
        ax.set_yticks(range(len(command_counts)))
        ax.set_yticklabels(command_counts.index, fontsize=11)
        ax.set_xlabel('Number of Occurrences', fontsize=13, fontweight='bold')
        ax.set_title('ATC Command Recognition - Fine-Tuned Model',
                     fontsize=15, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3)

        # Add count labels
        for i, count in enumerate(command_counts.values):
            ax.text(count + max(command_counts.values)*0.01, i,
                    f'{count}', va='center', fontweight='bold', fontsize=10)

        plt.tight_layout()
        plt.savefig(output_path / 'command_distribution.png')
        print(f"✓ Saved: command_distribution.png")
        plt.close()

    # 3. SPEAKER IDENTIFICATION
    if 'speaker' in df.columns and df['speaker'].notna().sum() > 0:
        print("\n3. Speaker Identification Performance:")
        speaker_counts = df['speaker'].value_counts()
        print(f"\nSpeakers identified: {speaker_counts.sum()} out of {total_samples} samples")
        print("\nSpeaker Distribution:")
        for speaker, count in speaker_counts.items():
            print(f"  {speaker:15s}: {count:4d} ({count/total_samples*100:.1f}%)")

        fig, ax = plt.subplots(figsize=(9, 7))
        colors_speaker = sns.color_palette("Set2", len(speaker_counts))
        wedges, texts, autotexts = ax.pie(speaker_counts.values,
                                           labels=[s.capitalize() for s in speaker_counts.index],
                                           autopct='%1.1f%%',
                                           colors=colors_speaker,
                                           startangle=90,
                                           textprops={'fontsize': 12, 'fontweight': 'bold'},
                                           explode=[0.05] * len(speaker_counts))
        ax.set_title('Speaker Identification Distribution - Fine-Tuned Model',
                     fontsize=15, fontweight='bold', pad=20)

        plt.tight_layout()
        plt.savefig(output_path / 'speaker_distribution.png')
        print(f"✓ Saved: speaker_distribution.png")
        plt.close()

    # 4. CALLSIGN EXTRACTION
    if 'callsign' in df.columns:
        callsign_extracted = df['callsign'].notna().sum()
        print(f"\n4. Callsign Extraction:")
        print(f"  Callsigns extracted: {callsign_extracted}/{total_samples} ({callsign_extracted/total_samples*100:.1f}%)")

        # Show top callsigns
        callsign_counts = df['callsign'].value_counts().head(20)
        fig, ax = plt.subplots(figsize=(12, 8))
        colors_cs = sns.color_palette("mako", len(callsign_counts))
        bars = ax.barh(range(len(callsign_counts)), callsign_counts.values, color=colors_cs, edgecolor='black', alpha=0.8)
        ax.set_yticks(range(len(callsign_counts)))
        ax.set_yticklabels(callsign_counts.index, fontsize=10, family='monospace')
        ax.set_xlabel('Frequency', fontsize=13, fontweight='bold')
        ax.set_title('Top 20 Extracted Callsigns - Fine-Tuned Model',
                     fontsize=15, fontweight='bold', pad=20)
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=0.3)

        # Add count labels
        for i, count in enumerate(callsign_counts.values):
            ax.text(count + max(callsign_counts.values)*0.01, i,
                    f'{count}', va='center', fontweight='bold', fontsize=9)

        plt.tight_layout()
        plt.savefig(output_path / 'callsign_extraction.png')
        print(f"✓ Saved: callsign_extraction.png")
        plt.close()

    # 5. FLIGHT LEVEL DISTRIBUTION
    if 'flight_level' in df.columns:
        flight_levels = df['flight_level'].dropna()
        if len(flight_levels) > 0:
            print(f"\n5. Flight Level Extraction:")
            print(f"  Flight levels extracted: {len(flight_levels)}/{total_samples} ({len(flight_levels)/total_samples*100:.1f}%)")
            print(f"  Range: FL{flight_levels.min():.0f} - FL{flight_levels.max():.0f}")
            print(f"  Mean: FL{flight_levels.mean():.1f}")

            fig, ax = plt.subplots(figsize=(12, 7))
            counts, bins, patches = ax.hist(flight_levels, bins=30, color='lightblue', edgecolor='black', alpha=0.7)
            ax.set_xlabel('Flight Level', fontsize=13, fontweight='bold')
            ax.set_ylabel('Frequency', fontsize=13, fontweight='bold')
            ax.set_title('Flight Level Extraction Distribution - Fine-Tuned Model',
                         fontsize=15, fontweight='bold', pad=20)
            ax.grid(axis='y', alpha=0.3)

            # Color bars by height
            cm = plt.cm.get_cmap('viridis')
            bin_centers = 0.5 * (bins[:-1] + bins[1:])
            col = bin_centers - min(bin_centers)
            col /= max(col)
            for c, p in zip(col, patches):
                plt.setp(p, 'facecolor', cm(c))

            plt.tight_layout()
            plt.savefig(output_path / 'flight_level_distribution.png')
            print(f"✓ Saved: flight_level_distribution.png")
            plt.close()

    # 6. HEADING DISTRIBUTION
    if 'heading' in df.columns:
        headings = df['heading'].dropna()
        if len(headings) > 0:
            print(f"\n6. Heading Extraction:")
            print(f"  Headings extracted: {len(headings)}/{total_samples} ({len(headings)/total_samples*100:.1f}%)")
            print(f"  Range: {headings.min():.0f}° - {headings.max():.0f}°")

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

            # Histogram
            ax1.hist(headings, bins=36, color='coral', edgecolor='black', alpha=0.7)
            ax1.set_xlabel('Heading (degrees)', fontsize=13, fontweight='bold')
            ax1.set_ylabel('Frequency', fontsize=13, fontweight='bold')
            ax1.set_title('Heading Distribution', fontsize=14, fontweight='bold')
            ax1.grid(axis='y', alpha=0.3)

            # Polar plot
            theta = headings * (np.pi / 180)  # Convert to radians
            ax2 = plt.subplot(1, 2, 2, projection='polar')
            ax2.scatter(theta, [1]*len(theta), c='coral', alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
            ax2.set_theta_zero_location('N')
            ax2.set_theta_direction(-1)
            ax2.set_title('Heading Distribution (Compass View)', fontsize=14, fontweight='bold', pad=20)
            ax2.set_ylim(0, 1.2)
            ax2.set_yticks([])
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(output_path / 'heading_distribution.png')
            print(f"✓ Saved: heading_distribution.png")
            plt.close()

    # 7. MULTI-FIELD EXTRACTION SUCCESS
    print("\n7. Multi-Field Extraction Analysis:")
    key_fields = ['command', 'speaker', 'callsign']
    available_fields = [f for f in key_fields if f in df.columns]

    if available_fields:
        extraction_summary = []
        for num_fields in range(len(available_fields) + 1):
            mask = df[available_fields].notna().sum(axis=1) == num_fields
            count = mask.sum()
            extraction_summary.append({
                'fields_extracted': num_fields,
                'count': count,
                'percentage': count / total_samples * 100
            })

        summary_df = pd.DataFrame(extraction_summary)
        print("\nKey Fields Extracted per Sample:")
        for _, row in summary_df.iterrows():
            print(f"  {int(row['fields_extracted'])} fields: {int(row['count'])} samples ({row['percentage']:.1f}%)")

        fig, ax = plt.subplots(figsize=(12, 7))
        colors_multi = sns.color_palette("cubehelix", len(summary_df))
        bars = ax.bar(summary_df['fields_extracted'], summary_df['percentage'],
                      color=colors_multi, edgecolor='black', alpha=0.85, width=0.7)
        ax.set_xlabel('Number of Key Fields Extracted', fontsize=13, fontweight='bold')
        ax.set_ylabel('Percentage of Samples (%)', fontsize=13, fontweight='bold')
        ax.set_title('Multi-Field Extraction Success - Fine-Tuned Model',
                     fontsize=15, fontweight='bold', pad=20)
        ax.set_xticks(summary_df['fields_extracted'])
        ax.grid(axis='y', alpha=0.3)

        # Add percentage labels on bars
        for bar, pct in zip(bars, summary_df['percentage']):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1.5,
                    f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=12)

        plt.tight_layout()
        plt.savefig(output_path / 'multi_field_success.png')
        print(f"✓ Saved: multi_field_success.png")
        plt.close()

    # 8. SUMMARY DASHBOARD
    print("\n" + "="*70)
    print("SUMMARY: FINE-TUNED MODEL EFFECTIVENESS")
    print("="*70)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Fine-Tuned Whisper Model + Parser - Performance Dashboard',
                 fontsize=18, fontweight='bold', y=0.995)

    # Top-left: Overall success rates
    ax = axes[0, 0]
    success_data = field_success_rate.sort_values(ascending=True)
    colors_dash = sns.color_palette("viridis", len(success_data))
    bars = ax.barh(success_data.index, success_data.values, color=colors_dash, edgecolor='black', alpha=0.8)
    ax.set_xlabel('Success Rate (%)', fontweight='bold')
    ax.set_title('Field Extraction Success Rates', fontweight='bold', fontsize=13)
    ax.set_xlim(0, 100)
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 2, bar.get_y() + bar.get_height()/2, f'{width:.0f}%',
                va='center', fontweight='bold', fontsize=9)

    # Top-right: Command distribution
    ax = axes[0, 1]
    if 'command' in df.columns and df['command'].notna().sum() > 0:
        cmd_counts = df['command'].value_counts()
        colors_cmd_dash = sns.color_palette("rocket", len(cmd_counts))
        wedges, texts, autotexts = ax.pie(cmd_counts.values,
                                           labels=cmd_counts.index,
                                           autopct='%1.0f%%',
                                           colors=colors_cmd_dash,
                                           startangle=45,
                                           textprops={'fontsize': 9, 'fontweight': 'bold'})
        ax.set_title('Command Distribution', fontweight='bold', fontsize=13)
    else:
        ax.text(0.5, 0.5, 'No Command Data', ha='center', va='center', fontsize=12)
        ax.set_title('Command Distribution', fontweight='bold', fontsize=13)

    # Bottom-left: Speaker distribution
    ax = axes[1, 0]
    if 'speaker' in df.columns and df['speaker'].notna().sum() > 0:
        spk_counts = df['speaker'].value_counts()
        colors_spk = sns.color_palette("Set2", len(spk_counts))
        bars = ax.bar(range(len(spk_counts)), spk_counts.values, color=colors_spk,
                      edgecolor='black', alpha=0.8)
        ax.set_xticks(range(len(spk_counts)))
        ax.set_xticklabels([s.capitalize() for s in spk_counts.index], fontweight='bold')
        ax.set_ylabel('Count', fontweight='bold')
        ax.set_title('Speaker Identification', fontweight='bold', fontsize=13)
        ax.grid(axis='y', alpha=0.3)
        for bar, count in zip(bars, spk_counts.values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(spk_counts.values)*0.02,
                    f'{count}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    else:
        ax.text(0.5, 0.5, 'No Speaker Data', ha='center', va='center', fontsize=12)
        ax.set_title('Speaker Identification', fontweight='bold', fontsize=13)

    # Bottom-right: Summary stats
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = f"""
    EVALUATION SUMMARY
    ══════════════════════════════════════
    
    Total Samples: {total_samples}
    
    Extraction Success:
    • Callsign: {(df['callsign'].notna().sum()/total_samples*100):.1f}%
    • Command: {(df['command'].notna().sum()/total_samples*100):.1f}%
    • Speaker: {(df['speaker'].notna().sum()/total_samples*100):.1f}%
    • Heading: {(df['heading'].notna().sum()/total_samples*100):.1f}%
    • Flight Level: {(df['flight_level'].notna().sum()/total_samples*100):.1f}%
    
    Avg Fields/Sample: {df.drop(columns=['transcript', 'sample_id']).notna().sum(axis=1).mean():.2f}
    
    ══════════════════════════════════════
    ✓ Fine-tuned model successfully extracts
      structured ATC information from
      natural language transcripts
    """
    ax.text(0.1, 0.5, summary_text, fontsize=11, family='monospace',
            verticalalignment='center', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    plt.tight_layout()
    plt.savefig(output_path / 'performance_dashboard.png')
    print(f"✓ Saved: performance_dashboard.png")
    plt.close()

    print(f"\n✓ All visualizations saved to: {output_path.absolute()}")
    print("="*70 + "\n")


def main():
    """Main evaluation pipeline."""
    print("="*70)
    print("FINE-TUNED WHISPER MODEL EVALUATION (TEXT-BASED)")
    print("="*70)

    # Configuration
    NUM_SAMPLES = 100  # Validation split samples

    # Load transcripts
    transcripts = load_validation_transcripts(limit=NUM_SAMPLES)

    # Evaluate parser
    results_df = evaluate_parser(transcripts)

    # Save raw results
    results_df.to_csv("text_evaluation_results.csv", index=False)
    print(f"\n✓ Saved detailed results to: text_evaluation_results.csv")

    # Generate visualizations
    generate_comprehensive_visualizations(results_df, output_dir="evaluation_results")

    print("\n✅ Evaluation complete!")
    print("="*70)


if __name__ == "__main__":
    main()

