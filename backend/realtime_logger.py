"""
Real-Time QBER Time-Series Logger

This module supports real-time visualization and attack detection claims
in the IEEE paper by logging QBER measurements over time.

Use cases:
- Section 6.4 Real-Time Visualization Effectiveness
- Live QBER monitoring plots
- Attack detection spike analysis
"""

import csv
import os
from datetime import datetime
from typing import Optional


class RealtimeLogger:
    """Logger for time-series QBER data during simulation."""
    
    def __init__(self, filename="qber_timeseries.csv"):
        self.filename = filename
        self.file_exists = os.path.isfile(filename)

        self.fields = [
            "timestamp",
            "run_id",
            "protocol",
            "distance_km",
            "time_step",
            "qber",
            "mode",  # For Aurora: "efficient" or "verified"
            "event"  # Optional: "normal", "attack_detected", "mode_switch"
        ]

        self._init_file()

    def _init_file(self):
        """Initialize CSV file with headers if it doesn't exist."""
        with open(self.filename, mode="a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            if not self.file_exists:
                writer.writeheader()

    def log_qber(
        self, 
        run_id: int, 
        protocol: str, 
        distance: float, 
        time_step: int, 
        qber: float,
        mode: Optional[str] = None,
        event: str = "normal"
    ):
        """
        Log a single QBER measurement at a specific time step.
        
        Args:
            run_id: Unique run identifier
            protocol: Protocol name (BB84, SARG04, AURORA-QKD)
            distance: Distance in km
            time_step: Current time step or block number
            qber: Measured QBER value
            mode: Optional mode indicator (for Aurora)
            event: Event type (normal, attack_detected, mode_switch)
        """
        with open(self.filename, mode="a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            writer.writerow({
                "timestamp": datetime.utcnow().isoformat(),
                "run_id": run_id,
                "protocol": protocol,
                "distance_km": distance,
                "time_step": time_step,
                "qber": qber,
                "mode": mode or "",
                "event": event
            })
    
    def get_filepath(self) -> str:
        """Return absolute path to the CSV file."""
        return os.path.abspath(self.filename)
