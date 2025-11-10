"""
Generate a word cloud visualization of extracted callsigns from the parser results.
"""

import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from collections import Counter
import os

def generate_callsign_wordcloud():
    """Generate and save a word cloud of callsigns from parser results."""

    # Read the parser results
    enhanced_file = 'enhanced_parser_results.csv'
    parser_outputs_file = 'parser_outputs.csv'

    callsigns = []

    # Read enhanced parser results
    if os.path.exists(enhanced_file):
        df_enhanced = pd.read_csv(enhanced_file)
        if 'callsign' in df_enhanced.columns:
            # Filter out empty/nan callsigns
            enhanced_callsigns = df_enhanced['callsign'].dropna()
            enhanced_callsigns = enhanced_callsigns[enhanced_callsigns != '']
            callsigns.extend(enhanced_callsigns.tolist())
            print(f"Loaded {len(enhanced_callsigns)} callsigns from enhanced parser results")

    # Read parser outputs
    if os.path.exists(parser_outputs_file):
        df_outputs = pd.read_csv(parser_outputs_file)
        if 'callsign' in df_outputs.columns:
            # Filter out empty/nan callsigns
            output_callsigns = df_outputs['callsign'].dropna()
            output_callsigns = output_callsigns[output_callsigns != '']
            callsigns.extend(output_callsigns.tolist())
            print(f"Loaded {len(output_callsigns)} callsigns from parser outputs")

    if not callsigns:
        print("No callsigns found in the data files!")
        return

    print(f"\nTotal callsigns collected: {len(callsigns)}")

    # Count callsign frequencies
    callsign_counter = Counter(callsigns)
    print(f"Unique callsigns: {len(callsign_counter)}")

    # Show top 10 most common callsigns
    print("\nTop 10 most common callsigns:")
    for callsign, count in callsign_counter.most_common(10):
        print(f"  {callsign}: {count}")

    # Create word cloud
    # Join all callsigns into a single string (with frequencies)
    text = ' '.join(callsigns)

    # Generate word cloud
    wordcloud = WordCloud(
        width=1600,
        height=800,
        background_color='white',
        colormap='viridis',
        relative_scaling=0.5,
        min_font_size=10,
        max_words=100,
        prefer_horizontal=0.7
    ).generate(text)

    # Create figure
    plt.figure(figsize=(20, 10))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title('ATC Callsign Word Cloud', fontsize=24, fontweight='bold', pad=20)
    plt.tight_layout(pad=0)

    # Save the word cloud
    output_dir = 'evaluation_results'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_path = os.path.join(output_dir, 'callsign_wordcloud.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nWord cloud saved to: {output_path}")

    # Also create a bar chart of top 20 callsigns
    plt.figure(figsize=(16, 10))
    top_20 = dict(callsign_counter.most_common(20))
    plt.barh(list(top_20.keys()), list(top_20.values()), color='steelblue')
    plt.xlabel('Frequency', fontsize=14, fontweight='bold')
    plt.ylabel('Callsign', fontsize=14, fontweight='bold')
    plt.title('Top 20 Most Extracted Callsigns', fontsize=16, fontweight='bold')
    plt.gca().invert_yaxis()  # Highest at top
    plt.tight_layout()

    bar_output_path = os.path.join(output_dir, 'callsign_frequency_bar.png')
    plt.savefig(bar_output_path, dpi=300, bbox_inches='tight')
    print(f"Bar chart saved to: {bar_output_path}")

    plt.show()

    print("\nVisualization complete!")

if __name__ == "__main__":
    generate_callsign_wordcloud()

