#!/usr/bin/env python3
"""
Master Script: Run All Experiments
Executes complete data collection pipeline for the paper
"""

import sys
import subprocess
from pathlib import Path
import time

def run_script(script_name, description):
    """Run a Python script and handle errors"""
    print(f"\n{'='*80}")
    print(f"STEP: {description}")
    print(f"{'='*80}\n")
    
    script_path = Path(__file__).parent / script_name
    
    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=False
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running {script_name}: {e}")
        return False

def main():
    """Run complete experiment pipeline"""
    
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║         AURORA-QKD - Results Section Data Collection             ║
║                  Complete Experiment Pipeline                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    start_time = time.time()
    
    # Step 1: Distance Sweep
    print("\n📊 PHASE 1: Distance-Dependent Performance (Figure 3)")
    print("This will run 750 simulations (3 protocols × 5 distances × 50 runs)")
    
    if not run_script('run_distance_sweep.py', 'Running distance sweep experiments'):
        print("❌ Distance sweep failed. Aborting.")
        return
    
    if not run_script('process_distance_results.py', 'Processing distance sweep results'):
        print("❌ Distance processing failed. Aborting.")
        return
    
    if not run_script('generate_figure_3.py', 'Generating Figure 3'):
        print("❌ Figure 3 generation failed. Aborting.")
        return
    
    # Step 2: QBER Sweep
    print("\n📊 PHASE 2: QBER Tolerance Analysis (Figure 4)")
    print("This will run 750 simulations (3 protocols × 5 QBER levels × 50 runs)")
    
    if not run_script('run_qber_sweep.py', 'Running QBER sweep experiments'):
        print("❌ QBER sweep failed. Aborting.")
        return
    
    if not run_script('process_qber_results.py', 'Processing QBER sweep results'):
        print("❌ QBER processing failed. Aborting.")
        return
    
    if not run_script('generate_figure_4.py', 'Generating Figure 4'):
        print("❌ Figure 4 generation failed. Aborting.")
        return
    
    # Summary
    total_time = time.time() - start_time
    
    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║                    ✅ ALL EXPERIMENTS COMPLETE!                   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

📊 Summary:
   • Total simulations: 1,500 (750 distance + 750 QBER)
   • Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)
   • Average per simulation: {(total_time/1500)*1000:.1f}ms

📁 Generated Files:
   • experiments/results/figures/fig3_distance_keyrate.png
   • experiments/results/figures/fig3_distance_keyrate.pdf
   • experiments/results/figures/fig4_qber_tolerance.png
   • experiments/results/figures/fig4_qber_tolerance.pdf

📋 Next Steps:
   1. Review the generated figures
   2. Check processed data in experiments/results/processed/
   3. Copy PNG/PDF files to your LaTeX paper directory
   4. Update Table II with baseline data (if needed)
   5. Verify all text claims match your actual data

🎯 Ready for paper submission!
    """)

if __name__ == '__main__':
    main()
