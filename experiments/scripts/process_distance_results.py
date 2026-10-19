#!/usr/bin/env python3
"""
Process Distance Sweep Results
Calculates statistics and prepares data for Figure 3
"""

import csv
import json
from pathlib import Path
from collections import defaultdict
import statistics

def process_distance_results():
    """Process raw distance sweep data"""
    
    # Load config
    config_path = Path(__file__).parent.parent / 'configs' / 'distance_sweep_config.json'
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Load raw data
    raw_data_file = Path(config['output']['raw_data_file'])
    if not raw_data_file.exists():
        print(f"❌ Raw data file not found: {raw_data_file}")
        print("Run: python experiments/scripts/run_distance_sweep.py first")
        return
    
    print(f"Processing {raw_data_file}...")
    
    # Read raw data
    with open(raw_data_file, 'r') as f:
        reader = csv.DictReader(f)
        raw_data = list(reader)
    
    # Group by protocol and distance
    grouped = defaultdict(lambda: defaultdict(list))
    
    for row in raw_data:
        protocol = row['protocol']
        distance = float(row['distance_km'])
        final_key = int(row['final_key_length'])
        
        grouped[protocol][distance].append(final_key)
    
    # Calculate statistics
    processed_data = []
    
    print(f"\n{'='*80}")
    print(f"{'Protocol':<12} {'Distance':<10} {'Mean':<10} {'Std Dev':<10} {'Key Rate':<12} {'N':<5}")
    print(f"{'='*80}")
    
    for protocol in sorted(grouped.keys()):
        for distance in sorted(grouped[protocol].keys()):
            values = grouped[protocol][distance]
            
            mean_final = statistics.mean(values)
            std_final = statistics.stdev(values) if len(values) > 1 else 0
            key_rate = mean_final / config['parameters']['raw_key_length']
            
            processed_data.append({
                'protocol': protocol,
                'distance_km': distance,
                'mean_final_key': mean_final,
                'std_final_key': std_final,
                'key_rate': key_rate,
                'n_runs': len(values)
            })
            
            print(f"{protocol:<12} {distance:<10.0f} {mean_final:<10.1f} {std_final:<10.1f} {key_rate:<12.3f} {len(values):<5}")
    
    print(f"{'='*80}\n")
    
    # Save processed data
    output_file = Path(config['output']['processed_file'])
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'protocol', 'distance_km', 'mean_final_key', 'std_final_key', 'key_rate', 'n_runs'
        ])
        writer.writeheader()
        writer.writerows(processed_data)
    
    print(f"✅ Processed data saved to: {output_file}")
    print(f"\nNext step: python experiments/scripts/generate_figure_3.py")
    
    return processed_data

if __name__ == '__main__':
    process_distance_results()
