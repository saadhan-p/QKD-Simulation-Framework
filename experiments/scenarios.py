"""
experiments/scenarios.py
========================
Deterministic channel traces and reproducible common random numbers for QKD strategies.

Trace scenarios:
 1. static_nominal: L = 20 km, e_channel = 1.5%
 2. step_e_channel: 1.0% -> 6.0% at block 20
 3. step_loss: 10 km -> 30 km at block 20
 4. linear_ramp_loss: 10 km -> 35 km ramp
 5. sinusoidal_drift_loss: +/- 3 dB oscillation around 20 km
 6. random_walk_e_channel: bounded Gaussian random walk [0.5%..7.0%]
 7. bursty_noise: episodes of 7.0% error at blocks 15..17 and 35..38
 8. detector_drift: eta_det drifts from 10% down to 5%
 9. eve_episode: intercept-resend on fraction f=0.16 raising error by 4.0% on blocks 20..35
 10. manipulation: periodic 1-block noise spikes to 9.0% to force safe fallback

RNG Architecture:
- Uses np.random.SeedSequence spawning.
- Separate streams for trace dynamics and per-block pulse simulations.
- Common random numbers: all strategies experience identical quantum channel traces
  and pulse random sequences on each block.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from backend.channel import attenuation


@dataclass(frozen=True)
class ChannelBlockState:
    """True physical channel and detector state for a single block."""
    block_idx: int
    L_km: float
    eta_ch: float
    eta_det: float
    e_channel: float
    dc: float
    dt: float

    @property
    def g(self) -> float:
        """Expected detection probability per pulse sent."""
        return self.eta_ch * self.eta_det + 2.0 * self.dc * self.dt


ScenarioGenerator = Callable[[int, int, np.random.Generator], list[ChannelBlockState]]


def scenario_static_nominal(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    L = 20.0
    eta_ch = attenuation(L)
    return [
        ChannelBlockState(
            block_idx=b,
            L_km=L,
            eta_ch=eta_ch,
            eta_det=0.10,
            e_channel=0.015,
            dc=100.0,
            dt=1e-9,
        )
        for b in range(num_blocks)
    ]


def scenario_step_e_channel(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    L = 20.0
    eta_ch = attenuation(L)
    trace = []
    step_point = 20
    for b in range(num_blocks):
        e_ch = 0.01 if b < step_point else 0.06
        trace.append(ChannelBlockState(
            block_idx=b,
            L_km=L,
            eta_ch=eta_ch,
            eta_det=0.10,
            e_channel=e_ch,
            dc=100.0,
            dt=1e-9,
        ))
    return trace


def scenario_step_loss(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    step_point = 20
    trace = []
    for b in range(num_blocks):
        L = 10.0 if b < step_point else 30.0
        trace.append(ChannelBlockState(
            block_idx=b,
            L_km=L,
            eta_ch=attenuation(L),
            eta_det=0.10,
            e_channel=0.015,
            dc=100.0,
            dt=1e-9,
        ))
    return trace


def scenario_linear_ramp_loss(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    trace = []
    for b in range(num_blocks):
        fraction = b / max(1, num_blocks - 1)
        L = 10.0 + fraction * 25.0  # 10 km to 35 km
        trace.append(ChannelBlockState(
            block_idx=b,
            L_km=L,
            eta_ch=attenuation(L),
            eta_det=0.10,
            e_channel=0.015,
            dc=100.0,
            dt=1e-9,
        ))
    return trace


def scenario_sinusoidal_drift_loss(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    trace = []
    # Nominal 20 km is 4.0 dB loss. Drifts +/- 3.0 dB (1.0 dB to 7.0 dB)
    period = 30.0
    for b in range(num_blocks):
        loss_db = 4.0 + 3.0 * math.sin(2.0 * math.pi * b / period)
        eta_ch = 10.0 ** (-loss_db / 10.0)
        # Invert attenuation to find equivalent L in km (alpha = 0.2 dB/km)
        L_eq = loss_db / 0.20
        trace.append(ChannelBlockState(
            block_idx=b,
            L_km=L_eq,
            eta_ch=eta_ch,
            eta_det=0.10,
            e_channel=0.015,
            dc=100.0,
            dt=1e-9,
        ))
    return trace


def scenario_random_walk_e_channel(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    L = 20.0
    eta_ch = attenuation(L)
    trace = []
    curr_e = 0.020
    for b in range(num_blocks):
        trace.append(ChannelBlockState(
            block_idx=b,
            L_km=L,
            eta_ch=eta_ch,
            eta_det=0.10,
            e_channel=curr_e,
            dc=100.0,
            dt=1e-9,
        ))
        step = rng.normal(loc=0.0, scale=0.004)
        curr_e = float(np.clip(curr_e + step, 0.005, 0.070))
    return trace


def scenario_bursty_noise(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    L = 20.0
    eta_ch = attenuation(L)
    trace = []
    for b in range(num_blocks):
        is_burst = (15 <= b <= 18) or (35 <= b <= 39)
        e_ch = 0.070 if is_burst else 0.015
        trace.append(ChannelBlockState(
            block_idx=b,
            L_km=L,
            eta_ch=eta_ch,
            eta_det=0.10,
            e_channel=e_ch,
            dc=100.0,
            dt=1e-9,
        ))
    return trace


def scenario_detector_drift(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    L = 20.0
    eta_ch = attenuation(L)
    trace = []
    for b in range(num_blocks):
        fraction = b / max(1, num_blocks - 1)
        eta_det = 0.10 - fraction * 0.05  # 10% down to 5%
        trace.append(ChannelBlockState(
            block_idx=b,
            L_km=L,
            eta_ch=eta_ch,
            eta_det=eta_det,
            e_channel=0.015,
            dc=100.0,
            dt=1e-9,
        ))
    return trace


def scenario_eve_episode(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    L = 20.0
    eta_ch = attenuation(L)
    trace = []
    # Eve intercept-resend on fraction f=0.16 during blocks 20..35
    for b in range(num_blocks):
        is_eve = (20 <= b <= 35)
        # Intercept-resend adds 0.25 * f error to observed error
        e_ch = 0.015 + (0.25 * 0.16 if is_eve else 0.0)  # 0.015 -> 0.055
        trace.append(ChannelBlockState(
            block_idx=b,
            L_km=L,
            eta_ch=eta_ch,
            eta_det=0.10,
            e_channel=e_ch,
            dc=100.0,
            dt=1e-9,
        ))
    return trace


def scenario_manipulation(num_blocks: int, seed: int, rng: np.random.Generator) -> list[ChannelBlockState]:
    L = 20.0
    eta_ch = attenuation(L)
    trace = []
    # Spikes error to 9% for 1 block every 8 blocks
    for b in range(num_blocks):
        is_spike = (b >= 12 and b % 8 == 0)
        e_ch = 0.090 if is_spike else 0.015
        trace.append(ChannelBlockState(
            block_idx=b,
            L_km=L,
            eta_ch=eta_ch,
            eta_det=0.10,
            e_channel=e_ch,
            dc=100.0,
            dt=1e-9,
        ))
    return trace


SCENARIO_REGISTRY: dict[str, ScenarioGenerator] = {
    "static_nominal": scenario_static_nominal,
    "step_e_channel": scenario_step_e_channel,
    "step_loss": scenario_step_loss,
    "linear_ramp_loss": scenario_linear_ramp_loss,
    "sinusoidal_drift_loss": scenario_sinusoidal_drift_loss,
    "random_walk_e_channel": scenario_random_walk_e_channel,
    "bursty_noise": scenario_bursty_noise,
    "detector_drift": scenario_detector_drift,
    "eve_episode": scenario_eve_episode,
    "manipulation": scenario_manipulation,
}


def get_scenario_trace(scenario_name: str, num_blocks: int, seed: int) -> list[ChannelBlockState]:
    """Generate deterministic channel trace for a scenario using a spawned RNG."""
    if scenario_name not in SCENARIO_REGISTRY:
        raise ValueError(f"Unknown scenario '{scenario_name}'. Available: {list(SCENARIO_REGISTRY.keys())}")

    ss = np.random.SeedSequence(seed)
    trace_ss, _ = ss.spawn(2)
    trace_rng = np.random.default_rng(trace_ss)
    generator = SCENARIO_REGISTRY[scenario_name]
    return generator(num_blocks, seed, trace_rng)


def get_block_pulse_seed(seed: int, block_idx: int) -> int:
    """Generate deterministic pulse simulation seed for a specific block using SeedSequence spawning."""
    ss = np.random.SeedSequence(seed)
    _, sim_ss = ss.spawn(2)
    # Spawn child seeds for up to 1000 blocks
    child_seeds = sim_ss.spawn(1000)
    return int(child_seeds[block_idx].generate_state(1)[0])
