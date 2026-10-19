"""
CSV Logger for QKD Experimental Data (IEEE Paper Ready)

This module provides production-ready logging for QKD simulation experiments.
Generates CSV files suitable for:
- Table IV (Baseline Performance)
- Distance vs Performance plots
- QBER tolerance analysis
- Statistical analysis with reproducible seeds
"""

import csv
import os
from datetime import datetime
from typing import Dict, Any


class ExperimentLogger:
    """Logger for per-run experimental data."""
    
    def __init__(self, filename="qkd_experiments.csv"):
        self.filename = filename
        self.file_exists = os.path.isfile(filename)

        self.fields = [
            "timestamp",
            "run_id",
            "protocol",
            "distance_km",
            "attenuation_db_per_km",
            "raw_key_length",
            "sifted_key_length",
            "final_key_length",
            "sifting_efficiency",
            "processing_efficiency",
            "qber",
            "noise_probability",
            "attack_type",
            "execution_time_ms",
            "random_seed",
            "secure",
            "status"
        ]

        self._init_file()

    def _init_file(self):
        """Initialize CSV file with headers if it doesn't exist."""
        with open(self.filename, mode="a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            if not self.file_exists:
                writer.writeheader()

    def log_run(self, data: Dict[str, Any]):
        """
        Log one simulation run.
        
        Args:
            data: Dictionary containing run metrics. Required keys:
                - run_id, protocol, distance_km, raw_key_length,
                - sifted_key_length, final_key_length, qber, etc.
        """
        data["timestamp"] = datetime.utcnow().isoformat()
        
        # Calculate efficiencies if not provided
        if "sifting_efficiency" not in data and "raw_key_length" in data:
            raw = data.get("raw_key_length", 1)
            sifted = data.get("sifted_key_length", 0)
            data["sifting_efficiency"] = (sifted / raw * 100) if raw > 0 else 0.0
            
        if "processing_efficiency" not in data and "raw_key_length" in data:
            raw = data.get("raw_key_length", 1)
            final = data.get("final_key_length", 0)
            data["processing_efficiency"] = (final / raw * 100) if raw > 0 else 0.0
        
        with open(self.filename, mode="a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            writer.writerow(data)
    
    def get_filepath(self) -> str:
        """Return absolute path to the CSV file."""
        return os.path.abspath(self.filename)
