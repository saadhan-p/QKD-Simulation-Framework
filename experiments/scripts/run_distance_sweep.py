#!/usr/bin/env python3
"""
Distance Sweep Experiment Runner
Generates data for Figure 3: Final Key Rate vs Distance
"""

import sys
import json
import csv
import time
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app import _run_simulation_pipeline


def load_config(config_path):
    """Load experiment configuration"""
    with open(config_path, 'r') as f:
        return json.load(f)

async def run_distance_sweep(config, base_seed: int | None = None):
    """Run distance sweep experiments with deterministic seeded streams."""
    seed = base_seed if base_seed is not None else config.get('parameters', {}).get('seed', 2024)
    print(f"Starting {config['experiment_name']}...")
    print(f"Description: {config['description']}")
    print(f"Base seed: {seed}")
    print(f"Total runs: {len(config['protocols'])} protocols × {len(config['parameters']['distances_km'])} distances × {config['parameters']['runs_per_config']} runs")
    
    total_runs = len(config['protocols']) * len(config['parameters']['distances_km']) * config['parameters']['runs_per_config']
    print(f"Total simulations: {total_runs}\n")
    
    ss = np.random.SeedSequence(seed)
    child_seeds = ss.spawn(total_runs)
    child_idx = 0

    # Prepare output file
    output_file = Path(config['output']['raw_data_file'])
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # CSV headers
    headers = [
        'timestamp', 'protocol', 'distance_km', 'qber', 'raw_key_length',
        'run_number', 'sifted_key_length', 'final_key_length', 
        'measured_qber', 'execution_time_ms'
    ]
    
    results = []
    run_count = 0
    start_time = time.time()
    
    # Run experiments
    for protocol in config['protocols']:
        for distance in config['parameters']['distances_km']:
            print(f"\n{'='*60}")
            print(f"Protocol: {protocol.upper()} | Distance: {distance} km")
            print(f"{'='*60}")
            
            for run_num in range(1, config['parameters']['runs_per_config'] + 1):
                run_count += 1
                run_seed = child_seeds[child_idx]
                child_idx += 1
                
                # Create simulation parameters
                params = {
                    'protocol': protocol,
                    'raw_key_length': config['parameters']['raw_key_length'],
                    'qber': config['parameters']['qber'],
                    'distance_km': distance,
                    'security_level': 'medium',
                    'error_correction': 'simple',
                    'seed': run_seed,
                }
                
                # Run simulation
                run_start = time.time()
                result = await _run_simulation_pipeline(params)
                run_time = (time.time() - run_start) * 1000  # Convert to ms
                
                # Extract results
                proto_res = result.get('protocol_result', {})
                sifted_len = proto_res.get('sifted_key_length', 0)
                final_len = result.get('final_key_length', 0)
                measured_qber = proto_res.get('estimated_qber', params['qber'])
                
                # Record result
                results.append({
                    'timestamp': datetime.now().isoformat(),
                    'protocol': protocol,
                    'distance_km': distance,
                    'qber': config['parameters']['qber'],
                    'raw_key_length': config['parameters']['raw_key_length'],
                    'run_number': run_num,
                    'sifted_key_length': sifted_len,
                    'final_key_length': final_len,
                    'measured_qber': measured_qber,
                    'execution_time_ms': run_time
                })
                
                # Progress update
                if run_num % 10 == 0 or run_num == config['parameters']['runs_per_config']:
                    progress = (run_count / total_runs) * 100
                    elapsed = time.time() - start_time
                    eta = (elapsed / run_count) * (total_runs - run_count)
                    print(f"  Run {run_num}/{config['parameters']['runs_per_config']} | "
                          f"Progress: {progress:.1f}% | "
                          f"ETA: {eta:.0f}s")
    
    # Save results to CSV
    print(f"\n{'='*60}")
    print(f"Saving results to {output_file}")
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results)

    from experiments.scripts.sweep_metadata import save_sweep_metadata
    meta_path = save_sweep_metadata(output_file, seed)
    print(f"Metadata saved to: {meta_path}")
    
    total_time = time.time() - start_time
    print(f"{'='*60}")
    print(f"✅ Experiment complete!")
    print(f"Total runs: {run_count}")
    print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"Average time per run: {(total_time/run_count)*1000:.1f}ms")
    print(f"Results saved to: {output_file}")
    
    return results


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run Distance sweep experiments")
    parser.add_argument("--config", type=str, default=None, help="Path to custom config JSON")
    parser.add_argument("--seed", type=int, default=None, help="Base random seed for reproducibility")
    args = parser.parse_args()

    if args.config:
        config_path = Path(args.config)
    else:
        config_path = Path(__file__).parent.parent / 'configs' / 'distance_sweep_config.json'
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    config = load_config(config_path)
    results = await run_distance_sweep(config, base_seed=args.seed)
    
    print(f"\n{'='*60}")
    print("Next steps:")
    print("1. Run: python experiments/scripts/process_distance_results.py")
    print("2. Run: python experiments/scripts/generate_figure_3.py")
    print(f"{'='*60}")

if __name__ == '__main__':
    asyncio.run(main())

