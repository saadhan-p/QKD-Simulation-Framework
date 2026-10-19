# QKD Simulation Framework

> **LICENSE PENDING - do not publish**

A comprehensive **Quantum Key Distribution (QKD)** simulation and visualization platform with support for multiple quantum cryptography protocols.

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.121-green.svg)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15-orange.svg)

## 🔐 What is QKD?

**Quantum Key Distribution** is a secure communication method that uses quantum mechanics principles to distribute cryptographic keys between two parties. Unlike classical cryptography, QKD's security is based on the laws of physics rather than computational complexity.

### Key Principles:
- **No-Cloning Theorem**: Quantum states cannot be copied perfectly
- **Measurement Disturbance**: Measuring a quantum system changes its state
- **Entanglement**: Quantum particles can be correlated across distance

This makes eavesdropping detectable and ensures information-theoretic security.

---

## 🎯 Project Overview

This project simulates three QKD protocols with a full-stack implementation:

### **Backend (FastAPI)**
- Real-time WebSocket communication
- Quantum protocol simulations (BB84, SARG04, Aurora)
- Channel modeling (attenuation, noise)
- Error correction algorithms
- Privacy amplification
- Security analysis

### **Frontend (PyQt5)**
- **Modern UI Experience**:
  - Interactive particle background effects
  - Glassmorphism design with dark/light themes
  - Animated toast notifications
  - Smooth transitions and modern widget styling
- **Visual Dashboard**:
  - Real-time QBER monitoring
  - Protocol comparison charts
  - Circular progress indicators
- **Export capabilities**: PNG, CSV, PDF support

---

## 🔬 Supported Protocols

### 1. **BB84** (Bennett-Brassard 1984)
- **Type**: Prepare-and-measure protocol
- **Bases**: Two non-orthogonal bases (Z, X)
- **Sifting**: ~50% efficiency (basis matching)
- **Security**: Proven unconditional security
- **Use Case**: Standard QKD baseline

### 2. **SARG04** (Scarani-Acín-Ribordy-Gisin 2004)
- **Type**: Enhanced prepare-and-measure
- **Improvement**: Better robustness against PNS attacks
- **Sifting**: ~60% efficiency (relaxed matching)
- **Security**: Enhanced for practical implementations
- **Use Case**: Improved efficiency variant

### 3. **Aurora** (Custom Protocol) ⭐
- **Type**: Hybrid adaptive protocol
- **Innovation**: Real-time adaptive mode switching
- **Modes**:
  - **Efficient Mode (EM)**: High-speed paired-state transmission with rescue protocol
  - **Verified Mode (VM)**: secure BB84-like transmission for high-noise segments
- **Special Features**:
  - **Entanglement Anchor**: continuous security verification via CHSH inequality
  - **Adaptive Switching**: Dynamic mode toggling based on live QBER thresholds
  - **Rescue Protocol**: Recovers bits from inconclusive measurements to boost efficiency
- **Efficiency**: ~35-50% (adaptive, security-focused)
- **Use Case**: Research and advanced scenarios

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    GUI Client (PyQt5)                   │
│  ┌──────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐    │
│  │ Overview │  │ Charts  │  │  Logs  │  │  Export  │    │
│  └──────────┘  └─────────┘  └────────┘  └──────────┘    │
└────────────────────────┬────────────────────────────────┘
                         │ WebSocket (ws://localhost:8080/ws)
                         ↓
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend Server                     │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Protocol Layer                                 │    │
│  │  ┌───────┐  ┌────────┐  ┌────────┐              │    │
│  │  │ BB84  │  │ SARG04 │  │ Aurora │              │    │
│  │  └───────┘  └────────┘  └────────┘              │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Channel Simulation                             │    │
│  │  • Attenuation  • Noise  • QBER                 │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Post-Processing Pipeline                       │    │
│  │  • Error Correction  • Privacy Amplification    │    │
│  │  • Security Analysis • Entropy Estimation       │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
Qkd/
├── backend/
│   ├── app.py                   # FastAPI server & WebSocket endpoints
│   ├── protocols/
│   │   ├── bb84.py              # BB84 protocol implementation
│   │   ├── sarg04.py            # SARG04 protocol implementation
│   │   └── aurora_qkd.py        # Aurora protocol implementation
│   ├── channel.py               # Quantum channel simulation
│   ├── error_correction.py      # Error correction algorithms
│   ├── privacy.py               # Privacy amplification
│   ├── security.py              # Security analysis tools
│   └── utils.py                 # Utility functions
├── client/
│   ├── gui_app.py               # Main PyQt5 GUI application
│   ├── api_client.py            # WebSocket client wrapper
│   ├── theme.py                 # UI theming
│   ├── animations.py            # UI animations
│   └── plugins/                 # Extensible plugin system
├── cli/
│   └── simulate.py              # Command-line interface
├── requirements.txt             # Python dependencies
└── start_backend.sh             # Backend startup script
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.13** (tested with Python 3.13.5)
- **pip** package manager

### Installation

1. **Clone/Navigate to the project root:**
   ```bash
   cd /path/to/Qkd
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

#### **Terminal 1 - Start Backend:**
```bash
./start_backend.sh localhost 8080
```

Expected output:
```
Starting QKD Backend Server...
Host: localhost
Port: 8080
API Docs will be available at: http://localhost:8080/docs

INFO: Uvicorn running on http://localhost:8080
INFO: Application startup complete.
```

#### **Terminal 2 - Start GUI:**
```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the GUI application
python client/gui_app.py
```

A PyQt5 window titled "QKD Visual Dashboard" will appear.

---

## 🎮 Usage Guide

### Running a Simulation

1. **Configure Parameters:**
   - **Server WS**: `ws://localhost:8080/ws` (default)
   - **Protocol**: Choose `bb84`, `sarg04`, or `aurora`
   - **Raw**: Number of raw key bits (e.g., `1000`)
   - **QBER**: Quantum bit error rate (e.g., `0.02` = 2%)
   - **Dist (km)**: Distance in kilometers (e.g., `10.0`)

2. **Start Simulation:**
   - Click the **Start** button
   - Watch progress bar and logs

3. **View Results:**
   - **Overview Tab**: Efficiency, Final Key Length, Security Status
   - **Charts Tab**: Live QBER plot, Sifted vs Final key comparison
   - **Logs Tab**: Detailed step-by-step JSON messages

4. **Export Results:**
   - Click **Export Report** for PDF
   - Use **Save QBER PNG** for chart images
   - Use **Save Run History CSV** for data analysis

### Keyboard Shortcuts
- `Ctrl+Left/Right`: Navigate between tabs
- Theme toggle: Click "Dark Mode" / "Light Mode" button

---

## 📊 Understanding the Results

### Key Metrics

**Efficiency**: `(Final Key Length / Sifted Key Length) × 100%`
- Measures how much of the sifted key survives error correction and privacy amplification
- Higher is better (but trades off with security)

**Final Key Length**: Number of secret bits after full processing
- Depends on: raw length, QBER, protocol, security level
- This is the actual usable cryptographic key

**Secure**: YES/NO
- Based on QBER threshold and entropy analysis
- YES: Key is information-theoretically secure
- NO: Eavesdropping detected or insufficient entropy

**QBER** (Quantum Bit Error Rate): `Errors / Total Bits`
- Expected: 1-5% (normal channel noise)
- Warning: >8% (possible eavesdropping)
- Abort: >11% (security compromised)

### Example Results

**BB84 Protocol** (1000 raw bits, QBER=2%):
```
Sifted: ~500 bits (50% sifting)
After EC: ~490 bits (fixed errors)
Final Key: ~220 bits (privacy amp)
Efficiency: 44%
Secure: YES
```

**Aurora Protocol** (1000 raw bits, QBER=2%):
```
Sifted: ~850 bits (85% in EM)
After EC: ~833 bits (fixed errors)
Final Key: ~375 bits (privacy amp)
Efficiency: 45%
Secure: YES
```

---

## 🔧 API Documentation

### REST Endpoints

**Health Check:**
```bash
GET http://localhost:8080/
Response: {"service": "qkd-backend", "status": "ok"}
```

**Synchronous Simulation:**
```bash
POST http://localhost:8080/simulate_sync
Body: {
  "protocol": "aurora",
  "raw_key_length": 1000,
  "qber": 0.02,
  "distance_km": 10.0,
  "error_correction": "simple",
  "security_level": "medium"
}
```

### WebSocket API

**Connect:** `ws://localhost:8080/ws`

**Send Simulation Request:**
```json
{
  "cmd": "simulate",
  "params": {
    "protocol": "bb84",
    "raw_key_length": 1000,
    "qber": 0.02,
    "distance_km": 10.0
  }
}
```

**Receive Messages:**
```json
{"step": "protocol", "data": {...}}
{"step": "channel", "qber": 0.02, ...}
{"step": "error_correction", "mismatches": 20, ...}
{"step": "privacy", "output_length": 375, ...}
{"step": "security", "secure": true, ...}
{"status": "done", "final_key_length": 375}
```

---

## 🧪 Testing

### Manual Testing
1. Run all three protocols with default parameters
2. Verify all produce valid keys with Secure=YES
3. Compare efficiencies: SARG04 > Aurora > BB84
4. Check charts populate correctly

### Expected Behavior
- **Low QBER** (1-3%): All protocols succeed
- **Medium QBER** (5-8%): Efficiency decreases, still secure
- **High QBER** (>11%): Security fails, simulation aborts

---

## 🎨 Features

✅ **Three QKD Protocols** - BB84, SARG04, Aurora  
✅ **Real-time Visualization** - Live charts and metrics  
✅ **WebSocket Streaming** - Step-by-step simulation updates  
✅ **Dark/Light Themes** - Beautiful UI with theme toggle  
✅ **Export Capabilities** - PNG, CSV, PDF reports  
✅ **Auto-reload Backend** - Changes reflect instantly  
✅ **Plugin System** - Extensible architecture  
✅ **Security Analysis** - Entropy and QBER-based verification  

---

## 🔬 Research & Educational Use

This simulator is ideal for:
- **Education**: Understanding QKD protocols visually
- **Research**: Testing new protocol variants (like Aurora)
- **Comparison**: Analyzing protocol efficiency and security trade-offs
- **Development**: Prototyping QKD systems before hardware implementation

### Extending the Framework

**Add a New Protocol:**
1. Create `backend/protocols/your_protocol.py`
2. Implement function: `run_your_protocol(raw_key_length, ...)`
3. Return dict with: `sifted_alice_bits`, `sifted_bob_bits`, `estimated_qber`
4. Register in `backend/app.py`
5. Add to GUI dropdown in `client/gui_app.py`

---

## 📚 References

- **BB84**: C. H. Bennett and G. Brassard, "Quantum Cryptography: Public key distribution and coin tossing", 1984
- **SARG04**: V. Scarani et al., "Quantum Cryptography Protocols Robust against Photon Number Splitting Attacks", 2004
- **QKD Overview**: N. Gisin et al., "Quantum Cryptography", Reviews of Modern Physics, 2002

---

## 🤝 Contributing

This is a research/educational project. Feel free to:
- Add new protocols
- Improve quantum channel models
- Enhance error correction algorithms
- Create new visualizations
- Add unit tests

---

## 📝 License
 
LICENSE PENDING - do not publish.
Educational and research use only.

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - Cross-platform GUI toolkit
- [pyqtgraph](http://www.pyqtgraph.org/) - Scientific graphics library
- [Uvicorn](https://www.uvicorn.org/) - ASGI server

---

## 📧 Support

For questions or issues:
1. Check the step-by-step guide in the artifacts
2. Review the API documentation above
3. Check backend logs (`http://localhost:8080/docs`)
4. Examine GUI logs tab for detailed messages

---

**Made with 🔐 for Quantum Cryptography Education and Research**
