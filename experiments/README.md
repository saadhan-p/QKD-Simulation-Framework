# AURORA-QKD Results Section - Experiment Automation

## 🎯 Quick Start

To collect ALL data for your Results section:

```bash
cd /Users/saadhan/Desktop/Qkd
python3 experiments/scripts/run_all_experiments.py
```

This will:
- Run 1,500 simulations (750 distance + 750 QBER)
- Process all results
- Generate Figure 3 and Figure 4
- Take approximately 30-45 minutes

## 📁 Directory Structure

```
experiments/
├── configs/
│   ├── distance_sweep_config.json    # Distance experiment settings
│   └── qber_sweep_config.json        # QBER experiment settings
├── scripts/
│   ├── run_all_experiments.py        # 🚀 Master script (run this!)
│   ├── run_distance_sweep.py         # Distance experiments
│   ├── run_qber_sweep.py             # QBER experiments
│   ├── process_distance_results.py   # Process distance data
│   ├── process_qber_results.py       # Process QBER data
│   ├── generate_figure_3.py          # Create Figure 3
│   └── generate_figure_4.py          # Create Figure 4
└── results/
    ├── raw_data/                     # Raw CSV data
    ├── processed/                    # Statistics & summaries
    └── figures/                      # PNG & PDF figures
```

## 🔧 Individual Experiment Steps

If you want to run experiments separately:

### Step 1: Distance Sweep (Figure 3)
```bash
# Run experiments (750 simulations)
python3 experiments/scripts/run_distance_sweep.py

# Process results
python3 experiments/scripts/process_distance_results.py

# Generate figure
python3 experiments/scripts/generate_figure_3.py
```

### Step 2: QBER Sweep (Figure 4)
```bash
# Run experiments (750 simulations)
python3 experiments/scripts/run_qber_sweep.py

# Process results
python3 experiments/scripts/process_qber_results.py

# Generate figure
python3 experiments/scripts/generate_figure_4.py
```

## 📊 Experiment Configurations

### Distance Sweep
- **Protocols**: BB84, SARG04, AURORA-QKD
- **Distances**: 5, 10, 20, 35, 50 km
- **QBER**: Fixed at 2%
- **Raw key length**: 1000 qubits
- **Runs per config**: 50
- **Total simulations**: 750

### QBER Sweep
- **Protocols**: BB84, SARG04, AURORA-QKD
- **QBER levels**: 2%, 5%, 8%, 11%, 15%
- **Distance**: Fixed at 20 km
- **Raw key length**: 1000 qubits
- **Runs per config**: 50
- **Total simulations**: 750

## 📈 Output Files

After running experiments, you'll have:

### Raw Data
- `experiments/results/raw_data/distance_sweep_runs.csv`
- `experiments/results/raw_data/qber_sweep_runs.csv`

### Processed Statistics
- `experiments/results/processed/figure_3_data.csv`
- `experiments/results/processed/figure_4_data.csv`

### Figures (for LaTeX paper)
- `experiments/results/figures/fig3_distance_keyrate.png` (300 DPI)
- `experiments/results/figures/fig3_distance_keyrate.pdf`
- `experiments/results/figures/fig4_qber_tolerance.png` (300 DPI)
- `experiments/results/figures/fig4_qber_tolerance.pdf`

## 🎯 Using Results in Your Paper

### 1. Copy Figures to LaTeX Directory
```bash
cp experiments/results/figures/fig3_distance_keyrate.png /path/to/latex/
cp experiments/results/figures/fig4_qber_tolerance.png /path/to/latex/
```

### 2. Update Table II (Baseline Performance)
The baseline data is already collected. Check:
- `/Users/saadhan/.gemini/antigravity/brain/2251a652-d9a2-4f20-b211-fe1f4671651e/baseline_performance_results.md`

### 3. Verify Text Claims
After processing QBER results, check the improvement percentage:
```bash
python3 experiments/scripts/process_qber_results.py
```

Look for the output:
```
Performance Improvements at 11% QBER:
BB84 at 11% QBER: XXX bits
AURORA at 11% QBER: YYY bits
Improvement: ZZ%
```

If different from 36%, update your paper text!

## 🔍 Customizing Experiments

### Change Number of Runs
Edit config files:
```json
{
  "parameters": {
    "runs_per_config": 100  // Change from 50 to 100
  }
}
```

### Add More Distance Points
Edit `distance_sweep_config.json`:
```json
{
  "parameters": {
    "distances_km": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
  }
}
```

### Add More QBER Levels
Edit `qber_sweep_config.json`:
```json
{
  "parameters": {
    "qber_levels": [0.01, 0.02, 0.03, 0.05, 0.08, 0.11, 0.15, 0.20]
  }
}
```

## 🐛 Troubleshooting

### Import Error: `qkd_simulator` not found
Make sure you're running from the project root:
```bash
cd /Users/saadhan/Desktop/Qkd
python3 experiments/scripts/run_all_experiments.py
```

### Matplotlib Error
Install matplotlib:
```bash
pip install matplotlib
```

### No Data Files
Make sure to run experiments before processing:
1. Run `run_distance_sweep.py` before `process_distance_results.py`
2. Run `run_qber_sweep.py` before `process_qber_results.py`

## ⏱️ Time Estimates

- **Distance sweep**: ~15-20 minutes
- **QBER sweep**: ~15-20 minutes
- **Processing & plotting**: ~1 minute
- **Total**: ~30-45 minutes

## 📋 Checklist for Paper Submission

- [ ] Run all experiments (`run_all_experiments.py`)
- [ ] Verify Figure 3 looks correct
- [ ] Verify Figure 4 looks correct
- [ ] Check improvement percentage matches paper claim
- [ ] Copy figures to LaTeX directory
- [ ] Update Table II with baseline data
- [ ] Compile LaTeX to verify figures appear
- [ ] Check all [DATA] placeholders are filled
- [ ] Verify text claims match actual data

## 🚀 Ready to Run!

Execute this command to start:
```bash
python3 experiments/scripts/run_all_experiments.py
```

Then sit back and let the automation do the work! ☕
