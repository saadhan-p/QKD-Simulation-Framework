"""
QFlux — QKD Real-Time Dashboard  (clean layout, no overlapping)

Layout:
  ┌──────────────────────── Header Bar ─────────────────────────────┐
  │  Title · Status · Metric strip · Anomaly badge                  │
  ├──────────────┬──────────────────────────────────────────────────┤
  │  Left        │  Tab area                                        │
  │  Sidebar     │    Live Monitor  |  Charts  |  Logs             │
  │  (controls)  │                                                  │
  └──────────────┴──────────────────────────────────────────────────┘

Sidebar holds: server URL, protocol, sliders (Distance/QBER/DetEff),
raw key length, Start/Stop/Export buttons, System Health.

Live Monitor tab: 4 metric cards + 2 rolling-buffer pyqtgraph plots.
"""

import sys
import asyncio
import json
import csv
import os
import time
from collections import deque
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QFrame,
    QFileDialog, QMessageBox, QTabWidget, QSlider, QDoubleSpinBox,
    QSpinBox, QGridLayout, QSizePolicy, QScrollArea,
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QPalette, QColor

# pyqtgraph
USE_PYQTGRAPH = True
try:
    import pyqtgraph as pg
    from pyqtgraph import exporters
    import numpy as np
    pg.setConfigOptions(antialias=True)
except Exception:
    USE_PYQTGRAPH = False

# fpdf
HAS_FPDF = True
try:
    from fpdf import FPDF
except Exception:
    HAS_FPDF = False

# websockets
try:
    import websockets as _websockets_lib
    HAS_WEBSOCKETS = True
except Exception:
    HAS_WEBSOCKETS = False

# ── Theme colours ─────────────────────────────────────────────────────────────
try:
    from .theme import Colors
    _ACCENT   = Colors.ACCENT_PRIMARY
    _BG_DARK  = Colors.BG_PRIMARY   if hasattr(Colors, "BG_PRIMARY")  else "#0d1117"
    _BG_CARD  = Colors.BG_CARD      if hasattr(Colors, "BG_CARD")     else "#161b22"
    _BG_PANEL = Colors.BG_SECONDARY if hasattr(Colors, "BG_SECONDARY") else "#13181f"
    _TXT_PRI  = Colors.TEXT_PRIMARY  if hasattr(Colors, "TEXT_PRIMARY") else "#e6edf3"
    _TXT_SEC  = Colors.TEXT_SECONDARY if hasattr(Colors, "TEXT_SECONDARY") else "#8b949e"
except Exception:
    _ACCENT   = "#58a6ff"
    _BG_DARK  = "#0d1117"
    _BG_CARD  = "#161b22"
    _BG_PANEL = "#13181f"
    _TXT_PRI  = "#e6edf3"
    _TXT_SEC  = "#8b949e"

QBER_WARN   = 0.11          # 11 % anomaly threshold
ROLLING_N   = 200
LATENCY_WARN_MS = 500

PROTOCOL_MAP = {
    "Standard BB84":   "bb84",
    "SARG04 Enhanced": "sarg04",
    "AURORA Protocol": "aurora",
}

# ──────────────────────────────────────────────────────────────────────────────
# Global stylesheet
# ──────────────────────────────────────────────────────────────────────────────
QSS = f"""
* {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 13px;
    color: {_TXT_PRI};
}}

QMainWindow, QWidget#root {{
    background: {_BG_DARK};
}}

/* ── Sidebar ── */
QFrame#sidebar {{
    background: {_BG_PANEL};
    border-right: 1px solid #21262d;
}}

/* ── Header ── */
QFrame#header {{
    background: {_BG_PANEL};
    border-bottom: 1px solid #21262d;
    min-height: 60px;
    max-height: 60px;
}}

QLabel#title {{
    font-size: 16px;
    font-weight: 700;
    color: {_TXT_PRI};
}}

QLabel#badge_ok {{
    color: #3fb950;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 10px;
    border: 1px solid #3fb950;
    border-radius: 10px;
}}

QLabel#badge_idle {{
    color: {_TXT_SEC};
    font-size: 12px;
    padding: 2px 10px;
    border: 1px solid #30363d;
    border-radius: 10px;
}}

QLabel#badge_warn {{
    color: #ff4444;
    font-size: 12px;
    font-weight: 700;
    padding: 2px 10px;
    border: 1px solid #ff4444;
    border-radius: 10px;
}}

QLabel#hdr_metric_val {{
    font-size: 15px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: {_ACCENT};
}}

QLabel#hdr_metric_lbl {{
    font-size: 10px;
    color: {_TXT_SEC};
}}

/* ── Metric cards ── */
QFrame#metric_card {{
    background: {_BG_CARD};
    border: 1px solid #21262d;
    border-radius: 8px;
}}

QLabel#card_val {{
    font-size: 26px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: {_ACCENT};
}}

QLabel#card_lbl {{
    font-size: 11px;
    color: {_TXT_SEC};
    font-weight: 600;
    letter-spacing: 1px;
}}

QLabel#card_sub {{
    font-size: 10px;
    color: {_TXT_SEC};
}}

/* ── Section labels ── */
QLabel#section {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: {_TXT_SEC};
    margin-top: 4px;
}}

/* ── Tab widget ── */
QTabWidget::pane {{
    background: {_BG_DARK};
    border: none;
}}

QTabBar::tab {{
    background: {_BG_PANEL};
    color: {_TXT_SEC};
    padding: 8px 22px;
    border: none;
    border-bottom: 2px solid transparent;
}}

QTabBar::tab:selected {{
    color: {_TXT_PRI};
    border-bottom: 2px solid {_ACCENT};
    background: {_BG_DARK};
}}

QTabBar::tab:hover:!selected {{
    color: {_TXT_PRI};
}}

/* ── Inputs ── */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
    background: #21262d;
    color: {_TXT_PRI};
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 5px 9px;
    selection-background-color: {_ACCENT};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {_ACCENT};
}}

QComboBox::drop-down {{ border: none; padding-right: 6px; }}
QComboBox QAbstractItemView {{
    background: #21262d;
    border: 1px solid #30363d;
    selection-background-color: {_ACCENT};
}}

/* ── Slider ── */
QSlider::groove:horizontal {{
    height: 5px;
    background: #30363d;
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {_ACCENT};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {_ACCENT};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}

/* ── Buttons ── */
QPushButton {{
    background: #21262d;
    color: {_TXT_PRI};
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}}
QPushButton:hover {{ background: #2d333b; border-color: {_ACCENT}; }}
QPushButton:pressed {{ background: #1c2128; }}
QPushButton:disabled {{ color: {_TXT_SEC}; }}

QPushButton#btn_primary {{
    background: {_ACCENT};
    color: #0d1117;
    border: none;
    font-weight: 700;
}}
QPushButton#btn_primary:hover {{ background: #79c0ff; }}
QPushButton#btn_primary:disabled {{ background: #21262d; color: {_TXT_SEC}; border: 1px solid #30363d; }}

QPushButton#btn_danger {{
    background: #da3633;
    color: #fff;
    border: none;
    font-weight: 600;
}}
QPushButton#btn_danger:hover {{ background: #f85149; }}
QPushButton#btn_danger:disabled {{ background: #21262d; color: {_TXT_SEC}; border: 1px solid #30363d; }}

/* ── TextEdit / log ── */
QTextEdit {{
    background: #0d1117;
    color: {_TXT_SEC};
    border: none;
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
}}

/* ── Scroll ── */
QScrollBar:vertical {{
    background: {_BG_PANEL};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #30363d;
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Health indicators ── */
QLabel#health_ok   {{ color: #3fb950; font-family: 'JetBrains Mono', monospace; font-size: 13px; }}
QLabel#health_warn {{ color: #ff4444; font-family: 'JetBrains Mono', monospace; font-size: 13px; }}

/* ── Divider ── */
QFrame#divider {{
    background: #21262d;
    max-height: 1px;
    min-height: 1px;
}}
"""


# ──────────────────────────────────────────────────────────────────────────────
# Slider + SpinBox composite widget
# ──────────────────────────────────────────────────────────────────────────────
class ParamSlider(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, label, lo, hi, step, default, decimals=2, unit="", parent=None):
        super().__init__(parent)
        self._lo = lo
        self._step = step
        self._steps = int(round((hi - lo) / step))
        self._busy = False

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 4)
        col.setSpacing(4)

        lbl = QLabel(label.upper())
        lbl.setObjectName("section")
        col.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(8)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self._steps)
        self.slider.setValue(self._to_idx(default))
        row.addWidget(self.slider, stretch=1)

        self.spin = QDoubleSpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(decimals)
        self.spin.setValue(default)
        self.spin.setSuffix(f" {unit}" if unit else "")
        self.spin.setFixedWidth(80)
        row.addWidget(self.spin)

        col.addLayout(row)

        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)

    def _to_idx(self, v): return int(round((v - self._lo) / self._step))
    def _to_val(self, i): return round(self._lo + i * self._step, 8)

    def _from_slider(self, i):
        if self._busy: return
        self._busy = True
        self.spin.setValue(self._to_val(i))
        self._busy = False
        self.valueChanged.emit(self.spin.value())

    def _from_spin(self, v):
        if self._busy: return
        self._busy = True
        self.slider.setValue(self._to_idx(v))
        self._busy = False
        self.valueChanged.emit(v)

    def value(self): return self.spin.value()


# ──────────────────────────────────────────────────────────────────────────────
# Stream Worker
# ──────────────────────────────────────────────────────────────────────────────
class StreamWorker(QThread):
    message      = pyqtSignal(dict)
    conn_status  = pyqtSignal(bool)   # True=connected, False=disconnected

    def __init__(self, url: str, init_params: dict, parent=None):
        super().__init__(parent)
        self._url    = url
        self._params = init_params
        self._stop   = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: Optional[asyncio.Queue] = None

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        except Exception as e:
            self.message.emit({"error": str(e)})
        finally:
            try: self._loop.close()
            except Exception: pass
        self.conn_status.emit(False)

    async def _main(self):
        if not HAS_WEBSOCKETS:
            self.message.emit({"error": "websockets package not found"})
            return
        self._queue = asyncio.Queue()
        self.conn_status.emit(True)
        try:
            async with _websockets_lib.connect(self._url, ping_interval=20) as ws:
                # push initial params
                await ws.send(json.dumps({"cmd": "update_params", "params": self._params}))

                async def _sender():
                    while not self._stop:
                        try:
                            msg = await asyncio.wait_for(self._queue.get(), timeout=0.3)
                            await ws.send(json.dumps(msg))
                        except asyncio.TimeoutError:
                            continue
                        except Exception:
                            break

                sender = asyncio.ensure_future(_sender())
                async for raw in ws:
                    if self._stop: break
                    try: data = json.loads(raw)
                    except Exception: data = {"raw": raw}
                    self.message.emit(data)
                sender.cancel()
        except Exception as e:
            self.message.emit({"error": str(e)})

    def push(self, params: dict):
        if self._queue and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._queue.put({"cmd": "update_params", "params": params}),
                self._loop,
            )

    def stop(self):
        self._stop = True


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def divider():
    f = QFrame()
    f.setObjectName("divider")
    f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return f


def section_label(text):
    lbl = QLabel(text.upper())
    lbl.setObjectName("section")
    return lbl


def export_csv(time_buf, qber_buf, kr_buf, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "qber", "key_rate_bps"])
        for t, q, k in zip(time_buf, qber_buf, kr_buf):
            w.writerow([round(t,3), round(q,5), round(k,2)])


# ──────────────────────────────────────────────────────────────────────────────
# Main Window
# ──────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QFlux")
        self.resize(1280, 780)
        self.setMinimumSize(900, 600)

        # rolling buffers
        self.buf_t  = deque(maxlen=ROLLING_N)
        self.buf_q  = deque(maxlen=ROLLING_N)
        self.buf_kr = deque(maxlen=ROLLING_N)
        self.buf_an = deque(maxlen=ROLLING_N)   # anomaly bools

        # health tracking
        self._fps_times: deque = deque(maxlen=30)
        self._last_msg_t = 0.0
        self._worker: Optional[StreamWorker] = None

        # warning blink
        self._blink_on = False
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(450)
        self._blink_timer.timeout.connect(self._blink)

        self._build()
        self.setStyleSheet(QSS)

    # ──────────────────────────────────────────────────────────────── build ──
    def _build(self):
        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        outer.addWidget(self._build_header())

        # Body
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_content(), stretch=1)
        outer.addLayout(body)

    # ── Header ───────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = QFrame(); hdr.setObjectName("header"); hdr.setFixedHeight(60)
        row = QHBoxLayout(hdr)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(16)

        title = QLabel("QFlux")
        title.setObjectName("title")
        row.addWidget(title)

        self.status_badge = QLabel("Idle")
        self.status_badge.setObjectName("badge_idle")
        row.addWidget(self.status_badge)

        row.addStretch()

        # anomaly badge (hidden by default)
        self.anomaly_badge = QLabel("QBER ANOMALY")
        self.anomaly_badge.setObjectName("badge_warn")
        self.anomaly_badge.setVisible(False)
        row.addWidget(self.anomaly_badge)

        row.addSpacing(24)

        # 3 quick-stat displays
        for attr, lbl in [("hdr_qber","QBER"), ("hdr_kr","Key Rate"), ("hdr_dist","Distance")]:
            col = QVBoxLayout(); col.setSpacing(0)
            vlbl = QLabel("—"); vlbl.setObjectName("hdr_metric_val")
            tlbl = QLabel(lbl); tlbl.setObjectName("hdr_metric_lbl")
            col.addWidget(vlbl)
            col.addWidget(tlbl)
            setattr(self, attr, vlbl)
            row.addLayout(col)
            if lbl != "Distance":
                sep = QFrame(); sep.setFrameShape(QFrame.VLine)
                sep.setStyleSheet("color: #21262d;"); sep.setFixedWidth(1)
                row.addWidget(sep)

        return hdr

    # ── Sidebar ──────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sidebar = QFrame(); sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)

        # wrap in scroll area so nothing gets clipped
        scroll = QScrollArea()
        scroll.setWidget(sidebar)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFixedWidth(260)
        scroll.setStyleSheet(f"QScrollArea {{ background: {_BG_PANEL}; border: none; }}")

        col = QVBoxLayout(sidebar)
        col.setContentsMargins(16, 16, 16, 16)
        col.setSpacing(10)

        # Server URL
        col.addWidget(section_label("Server URL"))
        self.url_input = QLineEdit("ws://localhost:8080/ws/stream")
        col.addWidget(self.url_input)

        col.addWidget(divider())

        # Protocol
        col.addWidget(section_label("Protocol"))
        self.proto_box = QComboBox()
        self.proto_box.addItems(list(PROTOCOL_MAP.keys()))
        col.addWidget(self.proto_box)

        col.addWidget(divider())

        # Sliders
        col.addWidget(section_label("Parameters"))

        self.sl_dist = ParamSlider("Distance", 5, 50, 1, 20, decimals=0, unit="km")
        self.sl_qber = ParamSlider("QBER Threshold", 0.001, 0.15, 0.001, 0.02, decimals=3)
        self.sl_eff  = ParamSlider("Detector Eff.", 0.10, 1.0, 0.01, 0.85, decimals=2)

        col.addWidget(self.sl_dist)
        col.addWidget(self.sl_qber)
        col.addWidget(self.sl_eff)

        col.addWidget(divider())

        # Raw key length
        col.addWidget(section_label("Raw Key Length"))
        self.raw_spin = QSpinBox()
        self.raw_spin.setRange(100, 50000)
        self.raw_spin.setValue(1000)
        self.raw_spin.setSingleStep(100)
        col.addWidget(self.raw_spin)

        col.addWidget(divider())

        # Buttons
        self.start_btn = QPushButton("Start Stream")
        self.start_btn.setObjectName("btn_primary")
        self.start_btn.setFixedHeight(40)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("btn_danger")
        self.stop_btn.setFixedHeight(36)
        self.stop_btn.setEnabled(False)

        self.export_btn = QPushButton("Export Report")
        self.export_btn.setFixedHeight(34)

        col.addWidget(self.start_btn)
        col.addWidget(self.stop_btn)
        col.addWidget(self.export_btn)

        col.addWidget(divider())

        # System Health
        col.addWidget(section_label("System Health"))
        grid = QGridLayout(); grid.setSpacing(6)
        grid.addWidget(QLabel("FPS:"),     0, 0)
        self.fps_lbl = QLabel("—"); self.fps_lbl.setObjectName("health_ok")
        grid.addWidget(self.fps_lbl,      0, 1)
        grid.addWidget(QLabel("Latency:"), 1, 0)
        self.lat_lbl = QLabel("— ms"); self.lat_lbl.setObjectName("health_ok")
        grid.addWidget(self.lat_lbl,      1, 1)
        col.addLayout(grid)

        col.addStretch()

        # Wire slider → live inject
        self.sl_dist.valueChanged.connect(lambda v: self._inject({"distance_km": v}))
        self.sl_qber.valueChanged.connect(lambda v: self._inject({"qber": v}))
        self.sl_eff.valueChanged.connect( lambda v: self._inject({"detector_efficiency": v}))

        # Wire buttons
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self._on_stop)
        self.export_btn.clicked.connect(self._on_export)

        return scroll

    # ── Content area ─────────────────────────────────────────────────────────
    def _build_content(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_live_tab(), "Live Monitor")
        self.tabs.addTab(self._build_logs_tab(), "Logs")
        return self.tabs

    # ── Live Monitor tab ──────────────────────────────────────────────────────
    def _build_live_tab(self):
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(16, 16, 16, 16)
        col.setSpacing(12)

        # Metric cards row
        cards = QHBoxLayout(); cards.setSpacing(12)
        self._card_qber   = self._metric_card("QBER",     "—",    "", "error rate")
        self._card_kr     = self._metric_card("Key Rate", "—",    "", "bits / second")
        self._card_dist   = self._metric_card("Distance", "— km", "", "channel distance")
        self._card_status = self._metric_card("Status",   "IDLE", "", "security status")
        for c in [self._card_qber, self._card_kr, self._card_dist, self._card_status]:
            cards.addWidget(c)
        col.addLayout(cards)

        if USE_PYQTGRAPH:
            # QBER plot
            q_lbl = QLabel("QBER  —  rolling buffer (last 200 points, 11% threshold dashed)")
            q_lbl.setObjectName("section")
            col.addWidget(q_lbl)

            self.pg_qber = pg.PlotWidget()
            self.pg_qber.setBackground(_BG_CARD)
            ax = self.pg_qber.getPlotItem()
            ax.getAxis("left").setPen(_TXT_SEC)
            ax.getAxis("bottom").setPen(_TXT_SEC)
            ax.getAxis("left").setTextPen(_TXT_SEC)
            ax.getAxis("bottom").setTextPen(_TXT_SEC)
            ax.setLabel("left", "QBER", color=_TXT_SEC)
            ax.setLabel("bottom", "time (s)", color=_TXT_SEC)
            self.pg_qber.showGrid(x=True, y=True, alpha=0.08)
            # threshold line
            self.pg_qber.addItem(pg.InfiniteLine(
                pos=QBER_WARN, angle=0,
                pen=pg.mkPen(color="#ff4444", width=1, style=Qt.DashLine)
            ))
            self._curve_ok  = self.pg_qber.plot(pen=pg.mkPen(_ACCENT, width=2))
            self._curve_err = self.pg_qber.plot(pen=pg.mkPen("#ff3333", width=2))
            col.addWidget(self.pg_qber, stretch=1)

            # Key Rate plot
            kr_lbl = QLabel("Key Rate  —  rolling buffer (last 200 points)")
            kr_lbl.setObjectName("section")
            col.addWidget(kr_lbl)

            self.pg_kr = pg.PlotWidget()
            self.pg_kr.setBackground(_BG_CARD)
            ax2 = self.pg_kr.getPlotItem()
            ax2.getAxis("left").setPen(_TXT_SEC)
            ax2.getAxis("bottom").setPen(_TXT_SEC)
            ax2.getAxis("left").setTextPen(_TXT_SEC)
            ax2.getAxis("bottom").setTextPen(_TXT_SEC)
            ax2.setLabel("left", "bps", color=_TXT_SEC)
            ax2.setLabel("bottom", "time (s)", color=_TXT_SEC)
            self.pg_kr.showGrid(x=True, y=True, alpha=0.08)
            self._curve_kr = self.pg_kr.plot(pen=pg.mkPen("#3fb950", width=2))
            col.addWidget(self.pg_kr, stretch=1)
        else:
            col.addWidget(QLabel("⚠  pyqtgraph not available — pip install pyqtgraph"))

        return page

    def _metric_card(self, title, value, icon, sub):
        f = QFrame(); f.setObjectName("metric_card")
        f.setFixedHeight(110)
        v = QVBoxLayout(f)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(2)

        top = QHBoxLayout(); top.setSpacing(4)
        lbl = QLabel(title.upper()); lbl.setObjectName("card_lbl")
        top.addWidget(lbl); top.addStretch()
        top.addWidget(QLabel(icon))
        v.addLayout(top)

        val = QLabel(value); val.setObjectName("card_val")
        v.addWidget(val)

        sub_lbl = QLabel(sub); sub_lbl.setObjectName("card_sub")
        v.addWidget(sub_lbl)
        v.addStretch()

        setattr(self, f"_val_{title.replace(' ','_').lower()}", val)
        return f

    def _set_card(self, attr, text):
        lbl: QLabel = getattr(self, f"_val_{attr}", None)
        if lbl: lbl.setText(text)

    # ── Logs tab ──────────────────────────────────────────────────────────────
    def _build_logs_tab(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        self.log = QTextEdit(); self.log.setReadOnly(True)
        v.addWidget(self.log)
        return page

    # ── Actions ───────────────────────────────────────────────────────────────
    def _on_start(self):
        url = self.url_input.text().strip()
        proto_key = PROTOCOL_MAP.get(self.proto_box.currentText(), "bb84")
        params = {
            "protocol":            proto_key,
            "raw_key_length":      self.raw_spin.value(),
            "distance_km":         self.sl_dist.value(),
            "qber":                self.sl_qber.value(),
            "detector_efficiency": self.sl_eff.value(),
            "security_level":      "medium",
            "error_correction":    "simple",
        }

        self.buf_t.clear(); self.buf_q.clear(); self.buf_kr.clear(); self.buf_an.clear()
        self._fps_times.clear(); self._last_msg_t = 0.0

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_badge.setText("Streaming")
        self.status_badge.setObjectName("badge_ok")
        self.status_badge.setStyleSheet("")   # force QSS re-read

        self._log(f"Connecting → {url}")
        self._log(f"Protocol: {self.proto_box.currentText()} | params: {json.dumps(params)}")

        self._worker = StreamWorker(url, params)
        self._worker.message.connect(self._on_msg)
        self._worker.conn_status.connect(self._on_conn)
        self._worker.start()

    def _on_stop(self):
        if self._worker:
            self._worker.stop()
        self.stop_btn.setEnabled(False)

    def _on_conn(self, connected: bool):
        if connected:
            self._log("Connected to stream")
        else:
            self._log("Stream disconnected")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_badge.setText("Idle")
            self.status_badge.setObjectName("badge_idle")
            self.status_badge.setStyleSheet("")
            self._blink_timer.stop()
            self.anomaly_badge.setVisible(False)

    def _inject(self, params: dict):
        if self._worker and self._worker.isRunning():
            self._worker.push(params)

    # ── Message handler ───────────────────────────────────────────────────────
    def _on_msg(self, data: dict):
        now = time.time()

        if "error" in data:
            self._log(f"Error: {data['error']}")
            return

        # latency
        if self._last_msg_t:
            lat = (now - self._last_msg_t) * 1000
            ok = lat <= LATENCY_WARN_MS
            self.lat_lbl.setText(f"{lat:.0f} ms")
            self.lat_lbl.setObjectName("health_ok" if ok else "health_warn")
            self.lat_lbl.setStyleSheet("")
        self._last_msg_t = now

        qber     = data.get("qber")
        key_rate = data.get("key_rate")
        dist     = data.get("distance_km")
        secure   = data.get("secure", True)
        anomaly  = data.get("anomaly", False)
        t        = data.get("time", now)

        # buffers
        if dist == 0:
            qber = 0.0
            key_rate = 0.0

        if qber is not None:
            self.buf_t.append(t)
            self.buf_q.append(qber)
            self.buf_kr.append(key_rate or 0.0)
            self.buf_an.append(anomaly)

        # cards
        if qber     is not None: self._set_card("qber",     f"{qber:.4f}")
        if key_rate is not None: self._set_card("key_rate", f"{key_rate:.0f} bps")
        if dist     is not None: self._set_card("distance", f"{dist:.1f} km")
        self._set_card("status", "SECURE" if secure else "⚠ INSECURE")

        # header strip
        if qber     is not None: self.hdr_qber.setText(f"{qber:.4f}")
        if key_rate is not None: self.hdr_kr.setText(f"{key_rate:.0f} bps")
        if dist     is not None: self.hdr_dist.setText(f"{dist:.1f} km")

        # anomaly blink
        if anomaly and not self._blink_timer.isActive():
            self._blink_timer.start()
        elif not anomaly:
            self._blink_timer.stop()
            self.anomaly_badge.setVisible(False)

        # plots + fps
        self._update_plots()

    def _blink(self):
        self._blink_on = not self._blink_on
        self.anomaly_badge.setVisible(self._blink_on)

    # ── Plots ─────────────────────────────────────────────────────────────────
    def _update_plots(self):
        if not USE_PYQTGRAPH or not self.buf_t:
            return

        now_fr = time.monotonic()
        self._fps_times.append(now_fr)
        if len(self._fps_times) >= 2:
            span = self._fps_times[-1] - self._fps_times[0]
            fps  = (len(self._fps_times) - 1) / span if span > 0 else 0
            self.fps_lbl.setText(f"{fps:.1f}")
            self.fps_lbl.setObjectName("health_ok" if fps >= 1 else "health_warn")
            self.fps_lbl.setStyleSheet("")

        xs  = np.array(self.buf_t,  float)
        ys  = np.array(self.buf_q,  float)
        krs = np.array(self.buf_kr, float)
        an  = list(self.buf_an)

        # split normal/anomaly
        ok_x, ok_y, err_x, err_y = [], [], [], []
        for x, y, a in zip(xs, ys, an):
            (err_x if a else ok_x).append(x)
            (err_y if a else ok_y).append(y)

        self._curve_ok.setData(ok_x, ok_y)
        self._curve_err.setData(err_x, err_y)

        x_max = xs[-1]; x_min = max(xs[0], x_max - 100)
        self.pg_qber.setXRange(x_min, x_max, padding=0.02)
        y_top = max(float(ys.max()) * 1.3, QBER_WARN * 1.4, 0.05)
        self.pg_qber.setYRange(0, y_top, padding=0)

        self._curve_kr.setData(xs, krs)
        self.pg_kr.setXRange(x_min, x_max, padding=0.02)
        if krs.max() > 0:
            self.pg_kr.setYRange(0, float(krs.max()) * 1.2, padding=0)

    # ── Export ────────────────────────────────────────────────────────────────
    def _on_export(self):
        tmp_png = "/tmp/qkd_snapshot.png"
        if USE_PYQTGRAPH and self.buf_t:
            try:
                exp = exporters.ImageExporter(self.pg_qber.plotItem)
                exp.parameters()["width"] = 1200
                exp.export(tmp_png)
            except Exception:
                try: self.pg_qber.grab().save(tmp_png)
                except Exception: pass

        tmp_csv = "/tmp/qkd_buffer.csv"
        try:
            export_csv(list(self.buf_t), list(self.buf_q), list(self.buf_kr), tmp_csv)
        except Exception:
            tmp_csv = None

        if HAS_FPDF:
            out, _ = QFileDialog.getSaveFileName(self, "Save PDF", "qkd_report.pdf", "PDF (*.pdf)")
            if out:
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_page()
                pdf.set_font("Arial", size=16)
                pdf.cell(0, 10, "QKD Dashboard Report", ln=True, align="C")
                pdf.set_font("Arial", size=12)
                for line in [
                    f"Ticks: {len(self.buf_t)}",
                    f"Avg QBER: {sum(self.buf_q)/len(self.buf_q):.5f}" if self.buf_q else "No data",
                ]:
                    pdf.multi_cell(0, 8, line); pdf.ln(1)
                if os.path.exists(tmp_png):
                    pdf.add_page()
                    pdf.image(tmp_png, x=10, y=20, w=pdf.w - 20)
                pdf.output(out)
                self._log(f"PDF saved: {out}")
                QMessageBox.information(self, "Export", f"Report saved:\n{out}")
        else:
            self._log(f"PNG: {tmp_png}  |  CSV: {tmp_csv}")
            QMessageBox.information(self, "Export", f"Saved:\n  PNG: {tmp_png}\n  CSV: {tmp_csv}")

    # ── Logging ───────────────────────────────────────────────────────────────
    def _log(self, msg: str):
        self.log.append(msg)


# ──────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
