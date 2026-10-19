"""FastAPI backend for QKD simulation with both WebSocket streaming and HTTP simulate.

New in this version:
  - /ws/stream  — Continuous broadcast loop. Runs simulation independently, emits
                  {"time", "qber", "key_rate", "distance_km", "attenuation", "secure"}
                  every STREAM_INTERVAL seconds. Accepts {"cmd": "update_params", "params": {...}}
                  mid-stream to hot-swap parameters without restarting.
  - /ws         — Original single-shot simulate endpoint (unchanged, kept for compatibility).
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import time
import math
import random

import numpy as np
import warnings

from .logger_config import configure_logging
from .protocols.bb84 import run_bb84
from .protocols.sarg04 import run_sarg04
from .protocols.aurora_qkd import run_aurora
from .protocols.b92 import run_b92
from .protocols.e91 import run_e91
from .channel import attenuation, apply_noise
from .error_correction import simple_correction, cascade_stub, ldpc_stub
from .privacy import compress_and_hash
from .security import min_entropy, security_status

logger = configure_logging(__name__)

app = FastAPI(title="QKD Simulation Server (backend)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
STREAM_INTERVAL = 0.5          # seconds between broadcast ticks
ROLLING_WINDOW  = 200          # how many ticks before we "reset" the time counter
QBER_ABORT_BB84   = 0.110
QBER_ABORT_SARG04 = 0.115
QBER_ABORT_AURORA = 0.125
QBER_ABORT_B92    = 0.045
QBER_ABORT_E91    = 0.110

# ──────────────────────────────────────────────────────────────────────────────
# Request model for HTTP endpoint
# ──────────────────────────────────────────────────────────────────────────────
class SimRequest(BaseModel):
    protocol: str = "bb84"
    raw_key_length: int = 1000
    distance_km: float = 10.0
    qber: float = 0.02
    security_level: str = "medium"
    error_correction: str = "simple"


# ──────────────────────────────────────────────────────────────────────────────
# HTTP root / simulate_sync
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"service": "qkd-backend", "status": "ok"}


@app.post("/simulate_sync")
async def simulate_sync(req: SimRequest) -> Dict[str, Any]:
    try:
        result = await _run_simulation_pipeline(dict(req))
        return {"status": "done", "result": result}
    except Exception as e:
        logger.exception("Simulation failed")
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# NEW: /ws/stream  — continuous broadcast endpoint
# ──────────────────────────────────────────────────────────────────────────────
@app.websocket("/ws/stream")
async def websocket_stream(ws: WebSocket):
    """
    Continuous-broadcast WebSocket.

    The client can optionally send:
        {"cmd": "update_params", "params": {"distance_km": 20, "qber": 0.05, ...}}

    The server broadcasts every STREAM_INTERVAL seconds:
        {
            "time": <float seconds since start>,
            "qber": <float>,
            "key_rate": <float bits/s>,
            "distance_km": <float>,
            "attenuation": <float>,
            "detector_efficiency": <float>,
            "secure": <bool>,
            "anomaly": <bool>   # True when qber > threshold
        }
    """
    await ws.accept()
    logger.info("Stream client connected")

    # ── Default params (can be overridden by client messages) ──
    params: Dict[str, Any] = {
        "protocol":           "bb84",
        "raw_key_length":     1000,
        "distance_km":        10.0,
        "qber":               0.02,
        "attenuation_db":     0.0,    # extra user-added attenuation
        "detector_efficiency": 0.85,
        "security_level":     "medium",
        "error_correction":   "simple",
    }

    start_time = time.time()
    tick = 0                          # rolling tick counter

    # Listen for incoming param-update messages without blocking the loop
    recv_queue: asyncio.Queue = asyncio.Queue()

    async def _reader():
        """Background task: read incoming WS messages into the queue."""
        try:
            while True:
                msg = await ws.receive_json()
                await recv_queue.put(msg)
        except Exception:
            pass  # connection closed

    reader_task = asyncio.ensure_future(_reader())

    try:
        while True:
            loop_start = time.monotonic()

            # ── Drain any pending param-update messages ──
            while not recv_queue.empty():
                msg = recv_queue.get_nowait()
                if msg.get("cmd") == "update_params":
                    new_p = msg.get("params", {})
                    params.update(new_p)
                    logger.info(f"Params updated: {new_p}")

            # ── Run one simulation tick ──
            try:
                payload = await _run_stream_tick(params, tick, start_time)
                await ws.send_json(payload)
            except Exception as e:
                logger.warning(f"Tick error: {e}")
                await ws.send_json({"error": str(e), "time": time.time() - start_time})

            tick += 1

            # ── Sleep for remainder of interval ──
            elapsed = time.monotonic() - loop_start
            sleep_time = max(0.0, STREAM_INTERVAL - elapsed)
            await asyncio.sleep(sleep_time)

    except WebSocketDisconnect:
        logger.info("Stream client disconnected")
    except Exception:
        logger.exception("Unexpected error in stream endpoint")
    finally:
        reader_task.cancel()


# ──────────────────────────────────────────────────────────────────────────────
# ORIGINAL: /ws — single-shot simulate (kept for compatibility)
#           Now also handles {"cmd": "update_params"} for live injection.
# ──────────────────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    Single-shot WebSocket endpoint.

    Commands accepted:
        {"cmd": "simulate",      "params": {...}}   – run a full simulation, stream steps
        {"cmd": "update_params", "params": {...}}   – update parameters for next simulation
    """
    await ws.accept()
    logger.info("WebSocket client connected")

    current_params: Dict[str, Any] = {}

    try:
        while True:
            msg = await ws.receive_json()
            cmd = msg.get("cmd")

            if cmd == "simulate":
                params = msg.get("params", {})
                params.update({k: v for k, v in current_params.items()
                                if k not in params})
                try:
                    async for update in _run_simulation_stream(params):
                        await ws.send_json(update)
                except Exception as e:
                    logger.exception("Error during simulation streaming")
                    await ws.send_json({"status": "error", "error": str(e)})

            elif cmd == "update_params":
                new_p = msg.get("params", {})
                current_params.update(new_p)
                logger.info(f"Queued param update: {new_p}")
                await ws.send_json({"status": "params_updated", "params": current_params})

            else:
                await ws.send_json({"status": "error", "error": "unknown command"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception:
        logger.exception("Unexpected error in websocket endpoint")


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_pa_factor(protocol: str, qber: float, security_level: str) -> float:
    """DEPRECATED: Heuristic per-protocol PA factor without quantum optics derivation.
    Retained solely for backward compatibility. Do not use for new simulations."""
    warnings.warn(
        "_get_pa_factor is deprecated and unphysical; use backend.postprocessing instead",
        DeprecationWarning,
        stacklevel=2,
    )
    proto = protocol.lower()
    if proto == "aurora":
        base_factor = 0.65
    elif proto == "sarg04":
        base_factor = 0.55
    elif proto == "b92":
        base_factor = 0.40
    elif proto == "e91":
        base_factor = 0.50
    else:
        base_factor = 0.48
    penalty = qber * 1.5
    factor = base_factor - penalty
    if security_level == "high":
        factor *= 0.85
    elif security_level == "low":
        factor *= 1.1
    return max(0.1, min(0.9, factor))


def _check_abort_threshold(protocol: str, qber: float) -> bool:
    proto = protocol.lower()
    if proto == "aurora":
        limit = QBER_ABORT_AURORA
    elif proto == "sarg04":
        limit = QBER_ABORT_SARG04
    elif proto == "b92":
        limit = QBER_ABORT_B92
    elif proto == "e91":
        limit = QBER_ABORT_E91
    else:
        limit = QBER_ABORT_BB84
    return qber > limit


def _run_protocol(
    protocol: str,
    raw: int,
    qber: float,
    distance_km: float = 10.0,
    rng: np.random.Generator | None = None,
    sample_min: int = 100,
):
    if rng is None:
        rng = np.random.default_rng()
    proto = protocol.lower()
    tx = attenuation(distance_km)
    if proto == "bb84":
        return run_bb84(n_sent=raw, rng=rng, eta_ch=tx, e_channel=qber, sample_min=sample_min)
    elif proto == "sarg04":
        return run_sarg04(n_sent=raw, rng=rng, eta_ch=tx, e_channel=qber, sample_min=sample_min)
    elif proto == "aurora":
        return run_aurora(
            raw_key_length=raw,
            block_size=200,
            p_anchor=0.05,
            paired_angle=0.2,
            rescue_fraction=0.25,
            eff_to_verif_qber=0.06,
            verif_to_eff_qber=0.03,
            qber=qber,
            rng=rng,
            legacy=False,
            sample_min=sample_min,
        )
    elif proto == "b92":
        return run_b92(raw)
    elif proto == "e91":
        return run_e91(raw)
    else:
        return run_sarg04(n_sent=raw, rng=rng, eta_ch=tx, e_channel=qber, sample_min=sample_min)


async def _run_stream_tick(params: Dict, tick: int, start_time: float) -> Dict:
    """
    Run one lightweight simulation tick and return the broadcast payload.
    Uses physically honest protocol engines with real channel loss.
    """
    protocol       = params.get("protocol", "bb84").lower()
    raw            = max(int(params.get("raw_key_length", 5000)), 5000)
    base_qber      = float(params.get("qber", 0.02))
    distance       = float(params.get("distance_km", 10.0))
    det_eff        = float(params.get("detector_efficiency", 0.10))
    tx             = attenuation(distance)
    effective_qber = max(0.0, min(0.5, base_qber))
    rng            = np.random.default_rng()

    if protocol in ("bb84", "sarg04", "aurora"):
        proto_res = _run_protocol(
            protocol, raw, effective_qber, distance_km=distance, rng=rng, sample_min=20
        )
        final_key_len = proto_res.get("final_key_length_asymptotic", 0)
        aborted = proto_res.get("aborted", False)
        measured_qber = proto_res.get("qber_est", effective_qber)
    else:
        proto_res = _run_protocol(protocol, raw, effective_qber, distance_km=distance, rng=rng)
        aborted = _check_abort_threshold(protocol, effective_qber)
        final_key_len = 0 if aborted else max(0, int(raw * 0.1))
        measured_qber = effective_qber

    secure = (not aborted) and (final_key_len > 0)
    key_rate = final_key_len / STREAM_INTERVAL
    elapsed = time.time() - start_time

    return {
        "time":               round(elapsed, 2),
        "qber":               round(measured_qber, 5),
        "key_rate":           round(key_rate, 1),
        "distance_km":        round(distance, 2),
        "attenuation":        round(tx, 4),
        "detector_efficiency": round(det_eff, 3),
        "secure":             secure,
        "anomaly":            aborted or (measured_qber > QBER_ABORT_BB84),
        "protocol":           protocol,
        "tick":               tick,
    }


async def _run_simulation_pipeline(params: Dict) -> Dict:
    protocol       = params.get("protocol", "bb84").lower()
    raw            = int(params.get("raw_key_length", 1000))
    distance       = float(params.get("distance_km", 10.0))
    qber           = float(params.get("qber", 0.02))
    ec_method      = params.get("error_correction", "simple")
    security_level = params.get("security_level", "medium")
    seed           = params.get("seed")
    rng            = np.random.default_rng(seed) if seed is not None else np.random.default_rng()

    tx = attenuation(distance)

    if protocol in ("bb84", "sarg04", "aurora"):
        proto_res = _run_protocol(protocol, raw, qber, distance_km=distance, rng=rng)
        final_len = proto_res.get("final_key_length_asymptotic", 0)
        sifted_len = proto_res.get("n_sifted", 0)
        measured_qber = proto_res.get("qber_est", qber)
        aborted = proto_res.get("aborted", False)
        secure = (not aborted) and (final_len > 0)

        return {
            "protocol_result": {
                "sifted_key_length": sifted_len,
                "estimated_qber": measured_qber,
                "raw_result": proto_res,
            },
            "channel":         {"distance_km": distance, "attenuation": tx, "qber": qber},
            "error_correction": {
                "method": "leak_ec_model",
                "leak_ec": proto_res.get("leak_ec", 0),
                "mismatches": 0,
                "final_errors": 0,
            },
            "privacy":         {
                "input_length": sifted_len - proto_res.get("n_sampled", 0),
                "output_length": final_len,
            },
            "security":        {
                "per_bit_entropy": 1.0 if secure else 0.0,
                "secure": secure,
                "aborted": aborted,
                "abort_reason": proto_res.get("abort_reason"),
            },
            "final_key_length": final_len,
            "aborted":         aborted,
        }
    else:
        # Legacy fallback for b92, e91
        proto_res = _run_protocol(protocol, raw, qber, distance_km=distance, rng=rng)
        sifted_alice = proto_res.get("sifted_alice_bits", [])
        sifted_bob   = proto_res.get("sifted_bob_bits", [])
        noisy_bob    = apply_noise(sifted_bob, qber)
        alice, corrected_bob, mismatches = simple_correction(sifted_alice, noisy_bob)
        qber_abort   = _check_abort_threshold(protocol, qber)
        if qber_abort:
            final_key = []
            secure = False
        else:
            pa_factor = _get_pa_factor(protocol, qber, security_level)
            out_len   = max(1, int(len(corrected_bob) * pa_factor))
            final_key = compress_and_hash(corrected_bob, out_len)
            secure    = True

        per_bit_entropy = min_entropy(final_key) if final_key else 0.0
        return {
            "protocol_result": proto_res,
            "channel":         {"distance_km": distance, "attenuation": tx, "qber": qber},
            "error_correction": {"method": ec_method, "mismatches": mismatches, "final_errors": 0},
            "privacy":         {"input_length": len(corrected_bob), "output_length": len(final_key)},
            "security":        {"per_bit_entropy": per_bit_entropy, "secure": secure},
            "final_key_length": len(final_key),
            "aborted":         qber_abort,
        }


async def _run_simulation_stream(params: Dict):
    protocol       = params.get("protocol", "bb84").lower()
    raw            = int(params.get("raw_key_length", 1000))
    distance       = float(params.get("distance_km", 10.0))
    qber           = float(params.get("qber", 0.02))
    seed           = params.get("seed")
    rng            = np.random.default_rng(seed) if seed is not None else np.random.default_rng()

    yield {"status": "start", "params": params}

    tx = attenuation(distance)
    yield {"step": "channel", "attenuation": round(tx, 4), "qber": qber, "distance_km": distance}
    await asyncio.sleep(0.01)

    if protocol in ("bb84", "sarg04", "aurora"):
        proto_res = _run_protocol(protocol, raw, qber, distance_km=distance, rng=rng)
        sifted_len = proto_res.get("n_sifted", 0)
        measured_qber = proto_res.get("qber_est", qber)
        final_len = proto_res.get("final_key_length_asymptotic", 0)
        aborted = proto_res.get("aborted", False)
        secure = (not aborted) and (final_len > 0)

        yield {"step": "protocol", "protocol": protocol, "sifted_len": sifted_len}
        await asyncio.sleep(0.01)

        yield {
            "step": "error_correction",
            "method": "leak_ec_model",
            "leak_ec_bits": proto_res.get("leak_ec", 0),
            "estimated_qber": measured_qber,
        }
        await asyncio.sleep(0.01)

        yield {
            "step": "privacy",
            "input_length": sifted_len - proto_res.get("n_sampled", 0),
            "output_length": final_len,
        }
        await asyncio.sleep(0.01)

        yield {
            "step": "security",
            "per_bit_entropy": 1.0 if secure else 0.0,
            "secure": secure,
            "aborted": aborted,
            "abort_reason": proto_res.get("abort_reason"),
        }
        await asyncio.sleep(0.01)

        yield {"status": "done", "final_key_length": final_len}
    else:
        # Legacy fallback
        res = await _run_simulation_pipeline(params)
        yield {"step": "protocol", "protocol": protocol, "data": res.get("protocol_result")}
        await asyncio.sleep(0.01)
        yield {"step": "security", "secure": res.get("security", {}).get("secure", False)}
        await asyncio.sleep(0.01)
        yield {"status": "done", "final_key_length": res.get("final_key_length", 0)}
