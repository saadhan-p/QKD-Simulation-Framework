#!/usr/bin/env python3
"""
Generate Figure 4: QBER Tolerance Analysis
"""

import csv
import json
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

def generate_figure_4():
    """Generate QBER vs final key length plot"""
    
    # Load config
    config_path = Path(__file__).parent.parent / 'configs' / 'qber_sweep_config.json'
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Load processed data
    data_file = Path(config['output']['processed_file'])
    if not data_file.exists():
        print(f"❌ Processed data file not found: {data_file}")
        print("Run: python experiments/scripts/process_qber_results.py first")
        return
    
    print(f"Loading data from {data_file}...")
    
    with open(data_file, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)
    
    # Organize data by protocol
    protocols = {}
    for row in data:
        protocol = row['protocol']
        if protocol not in protocols:
            protocols[protocol] = {'qber_percent': [], 'mean_keys': [], 'std_devs': []}
        
        protocols[protocol]['qber_percent'].append(float(row['qber_percent']))
        protocols[protocol]['mean_keys'].append(float(row['mean_final_key']))
        protocols[protocol]['std_devs'].append(float(row['std_final_key']))
    
    # Create figure
    plt.figure(figsize=(10, 7))
    
    # Plot styling
    colors = {
        'bb84': '#1f77b4',
        'sarg04': '#ff7f0e',
        'aurora': '#2ca02c'
    }
    
    markers = {
        'bb84': 'o',
        'sarg04': 's',
        'aurora': '^'
    }
    
    labels = {
        'bb84': 'BB84',
        'sarg04': 'SARG04',
        'aurora': 'AURORA-QKD'
    }
    
    # Plot each protocol
    for protocol in sorted(protocols.keys()):
        plt.errorbar(
            protocols[protocol]['qber_percent'],
            protocols[protocol]['mean_keys'],
            yerr=protocols[protocol]['std_devs'],
            marker=markers.get(protocol, 'o'),
            markersize=10,
            linewidth=2.5,
            capsize=5,
            capthick=2,
            label=labels.get(protocol, protocol.upper()),
            color=colors.get(protocol, '#000000')
        )
    
    # Add security threshold line
    plt.axvline(x=11, color='red', linestyle='--', linewidth=2.5, alpha=0.7, zorder=0)
    
    # Get y-axis limits to position text
    ymin, ymax = plt.ylim()
    text_y = ymax * 0.85
    
    plt.text(11.5, text_y, 'Security\nThreshold', fontsize=12, color='red', 
             fontweight='bold', va='center', ha='left')
    
    # Formatting
    plt.xlabel('QBER (%)', fontsize=14, fontweight='bold')
    plt.ylabel('Final Key Length (bits)', fontsize=14, fontweight='bold')
    plt.title('QKD Protocol QBER Tolerance (20 km)', fontsize=16, fontweight='bold', pad=20)
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.legend(fontsize=13, loc='upper right', framealpha=0.9)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.tight_layout()
    
    # Save figure
    output_file = Path(config['output']['figure_file'])
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Figure saved to: {output_file}")
    print(f"   Resolution: 300 DPI")
    print(f"   Format: PNG")
    
    # Also save as PDF for LaTeX
    pdf_file = output_file.with_suffix('.pdf')
    plt.savefig(pdf_file, bbox_inches='tight')
    print(f"✅ PDF version saved to: {pdf_file}")
    
    plt.close()
    
    print(f"\n{'='*60}")
    print("Figure 4 generation complete!")
    print(f"Copy {output_file.name} to your LaTeX paper directory")
    print(f"{'='*60}")

if __name__ == '__main__':
    generate_figure_4()
