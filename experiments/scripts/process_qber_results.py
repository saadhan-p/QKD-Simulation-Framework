#!/usr/bin/env python3
"""
Process QBER Sweep Results
Calculates statistics and prepares data for Figure 4
"""

import csv
import json
from pathlib import Path
from collections import defaultdict
import statistics

def process_qber_results():
    """Process raw QBER sweep data"""
    
    # Load config
    config_path = Path(__file__).parent.parent / 'configs' / 'qber_sweep_config.json'
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Load raw data
    raw_data_file = Path(config['output']['raw_data_file'])
    if not raw_data_file.exists():
        print(f"❌ Raw data file not found: {raw_data_file}")
        print("Run: python experiments/scripts/run_qber_sweep.py first")
        return
    
    print(f"Processing {raw_data_file}...")
    
    # Read raw data
    with open(raw_data_file, 'r') as f:
        reader = csv.DictReader(f)
        raw_data = list(reader)
    
    # Group by protocol and QBER
    grouped = defaultdict(lambda: defaultdict(list))
    
    for row in raw_data:
        protocol = row['protocol']
        qber = float(row['qber'])
        final_key = int(row['final_key_length'])
        
        grouped[protocol][qber].append(final_key)
    
    # Calculate statistics
    processed_data = []
    
    print(f"\n{'='*80}")
    print(f"{'Protocol':<12} {'QBER %':<10} {'Mean':<10} {'Std Dev':<10} {'Min':<10} {'Max':<10} {'N':<5}")
    print(f"{'='*80}")
    
    for protocol in sorted(grouped.keys()):
        for qber in sorted(grouped[protocol].keys()):
            values = grouped[protocol][qber]
            
            mean_final = statistics.mean(values)
            std_final = statistics.stdev(values) if len(values) > 1 else 0
            min_final = min(values)
            max_final = max(values)
            
            processed_data.append({
                'protocol': protocol,
                'qber': qber,
                'qber_percent': qber * 100,
                'mean_final_key': mean_final,
                'std_final_key': std_final,
                'min_final_key': min_final,
                'max_final_key': max_final,
                'n_runs': len(values)
            })
            
            print(f"{protocol:<12} {qber*100:<10.0f} {mean_final:<10.1f} {std_final:<10.1f} {min_final:<10.0f} {max_final:<10.0f} {len(values):<5}")
    
    print(f"{'='*80}\n")
    
    # Calculate improvement percentages
    print("Performance Improvements at 11% QBER:")
    print(f"{'='*60}")
    
    # Find values at 11% QBER
    bb84_11 = next((d['mean_final_key'] for d in processed_data if d['protocol'] == 'bb84' and abs(d['qber'] - 0.11) < 0.001), None)
    aurora_11 = next((d['mean_final_key'] for d in processed_data if d['protocol'] == 'aurora' and abs(d['qber'] - 0.11) < 0.001), None)
    
    if bb84_11 and aurora_11:
        improvement = ((aurora_11 - bb84_11) / bb84_11) * 100
        print(f"BB84 at 11% QBER: {bb84_11:.1f} bits")
        print(f"AURORA at 11% QBER: {aurora_11:.1f} bits")
        print(f"Improvement: {improvement:.1f}%")
        print(f"\n⚠️  Update paper text if different from claimed 36%!")
    print(f"{'='*60}\n")
    
    # Save processed data
    output_file = Path(config['output']['processed_file'])
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'protocol', 'qber', 'qber_percent', 'mean_final_key', 'std_final_key',
            'min_final_key', 'max_final_key', 'n_runs'
        ])
        writer.writeheader()
        writer.writerows(processed_data)
    
    print(f"✅ Processed data saved to: {output_file}")
    print(f"\nNext step: python experiments/scripts/generate_figure_4.py")
    
    return processed_data

if __name__ == '__main__':
    process_qber_results()
