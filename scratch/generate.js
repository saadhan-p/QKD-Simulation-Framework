
const r   = (t, o={}) => t;
const rb  = (t, o={}) => `\\textbf{${t}}`;
const ri  = (t, o={}) => `\\textit{${t}}`;
const rbi = (t, o={}) => `\\textbf{\\textit{${t}}}`;
const rs  = (t, o={}) => t;
const rsb = (t, o={}) => `\\textbf{${t}}`;
const rc  = (t, o={}) => `\\texttt{${t}}`;

const p = (c, o={}) => (Array.isArray(c)?c.join(''):c) + '\n\n';
const pC  = p;
const pL  = p;
const txt = (t, o={}) => t + '\n\n';
const gap = (n=1) => Array.from({length:n}, () => '\n');

const sec  = t => `\\section{${t.replace(/^\d+\s+/, '')}}\n`;
const sub  = t => `\\subsection{${t.replace(/^\d+\.\d+\s+/, '')}}\n`;
const sub2 = t => `\\subsubsection{${t.replace(/^\d+\.\d+\.\d+\s+/, '')}}\n`;

const tCap = t => `\\captionof{table}{${t.replace(/^Table \d+\s+/, '')}}\n`;
const fCap = t => `\\captionof{figure}{${t.replace(/^Fig\.\s*\d+\s+/, '')}}\n`;

const ref = t => `\\bibitem{ref${Math.random().toString(36).substring(7)}} ${t.replace(/^\\[\d+\\]\s+/, '')}\n`;

let inBullets = false;
const bul = t => {
    return `\\item ${t}\n`;
};

const figBox = t => `\\begin{figure}[hbt!]\n\\centering\n\\framebox{\\parbox{0.8\\textwidth}{\\centering ${t}}}\n\\end{figure}\n`;

const mkT = (headers, rows, cols, shade) => {
    let out = `\\begin{table}[hbt!]\n\\centering\n\\begin{tabular}{|${headers.map(()=>'c').join('|')}|}\n\\hline\n`;
    out += headers.map(rsb).join(' & ') + ' \\\\\n\\hline\n';
    rows.forEach(row => {
        out += row.map(rs).join(' & ') + ' \\\\\n';
    });
    out += `\\hline\n\\end{tabular}\n\\end{table}\n`;
    return out;
};

const infoBox = rows => {
    let out = `\\begin{center}\n\\begin{tabular}{ll}\n`;
    rows.forEach(([lbl, val]) => {
        out += `\\textbf{${lbl}} & ${val} \\\\\n`;
    });
    out += `\\end{tabular}\n\\end{center}\n`;
    return out;
};

const Paragraph = class {
    constructor({children}) {
        this.children = children;
    }
    toString() {
        if (!this.children) return '';
        return this.children.map(c => c ? c.toString() : '').join('');
    }
};

const TextRun = class {
    constructor({children, text}) {
        if (text) this.val = text;
        else if (children) this.val = children.join('');
        else this.val = '';
    }
    toString() {
        if (this.val === PageNumber.CURRENT) return "1";
        return this.val;
    }
};

const AlignmentType = { JUSTIFIED: 1, CENTER: 2, RIGHT: 3, LEFT: 4 };
const BorderStyle = { SINGLE: 1, NONE: 0 };
const WidthType = { DXA: 1 };
const ShadingType = { CLEAR: 1 };
const LevelFormat = { BULLET: 1 };
const Header = class {};
const Footer = class {};


const PageNumber = { CURRENT: Symbol("CURRENT_PAGE") };

const children = [

      // ── Submission box ──────────────────────────────────────────────────────
      infoBox([
        ["Target Journal:  ", "EPJ Quantum Technology — SpringerOpen"],
        ["Manuscript Type: ", "Full Research Article"],
        ["Subject Areas:   ", "Quantum Key Distribution · Adaptive Protocols · Real-Time Visualization · HCI"],
        ["Date:            ", "May 2026"],
        ["OA Agreement:    ", "Amrita Vishwa Vidyapeetham — Springer Nature Institutional Agreement (APC Waived)"],
      ]),
      ...gap(1),

      // ── TITLE ──────────────────────────────────────────────────────────────
      pC([rb("Aurora-QFlux: A Full-Stack Adaptive Quantum Key Distribution\nSimulation and Real-Time Visualization Framework",{size:29})],
        {spacing:{before:120,after:160}}),

      pC([r("Adwitiya Mukhopadhyay",{size:22}),r("  ·  ",{size:22}),
          r("Saadhan P",{size:22}),r("  ·  ",{size:22}),
          r("Rashmitha S",{size:22})],{spacing:{after:60}}),
      pC([ri("Amrita School of Computing, Amrita Vishwa Vidyapeetham, Mysuru, Karnataka, India",{size:19})],{spacing:{after:60}}),
      pC([rs("adwitiya@my.amrita.edu  ·  saadhan275@gmail.com  ·  rashmithas588@gmail.com")],{spacing:{after:60}}),
      pC([rs("Corresponding author: Adwitiya Mukhopadhyay  |  adwitiya@my.amrita.edu")],{spacing:{after:240}}),

      // ── ABSTRACT ───────────────────────────────────────────────────────────
      pL([rb("Abstract",{size:22})],{spacing:{before:0,after:80}}),
      new Paragraph({
        alignment:AlignmentType.JUSTIFIED,
        spacing:{line:264,before:0,after:120},
        indent:{left:720,right:720},
        children:[r(
          "Quantum Key Distribution (QKD) offers information-theoretically secure key exchange grounded in "+
          "the laws of quantum mechanics, yet practical deployments face a persistent trade-off between "+
          "sifting efficiency and robustness against channel noise. Existing protocols such as BB84 and "+
          "SARG04 operate with fixed sifting strategies, yielding 50.1% and 60.1% sifting efficiency "+
          "respectively under low-noise conditions, and cannot dynamically adapt to deteriorating channel "+
          "quality. This paper presents Aurora-QFlux, an integrated full-stack framework comprising two "+
          "equally weighted contributions: (1) Aurora, a novel adaptive hybrid QKD protocol that "+
          "dynamically toggles between a high-efficiency Efficient Mode and a secure Verified Mode based "+
          "on real-time QBER estimation and continuous CHSH entanglement anchor verification, and "+
          "(2) QFlux, a GPU-accelerated real-time visualization dashboard delivering telemetry at "+
          "42.4 ms mean end-to-end latency via WebSocket streaming and circular buffer management. "+
          "Experimental evaluation across 167 runs per condition — spanning QBER values of 2%–15% "+
          "and distances of 5–50 km — demonstrates that Aurora achieves 89.0%–93.8% sifting efficiency "+
          "and produces 2.45×–2.90× more final secure key bits than BB84 across all tested noise "+
          "levels while maintaining security. At QBER = 15%, all protocols correctly abort with zero "+
          "key output, validating Aurora's security termination mechanisms. Distance sweeps confirm "+
          "algorithmic stability (final key std dev < 0.4 bits across 5–50 km). A controlled "+
          "usability study (n = 12) demonstrates that QFlux reduces parameter tuning time by 74% "+
          "and NASA-TLX cognitive workload by 52% versus batch-processing baselines (SUS = 82, Excellent). "+
          "Aurora-QFlux provides the quantum communication community with a unified protocol research "+
          "and operational monitoring platform."
        )]
      }),
      new Paragraph({
        alignment:AlignmentType.JUSTIFIED,
        indent:{left:720,right:720},
        spacing:{after:240},
        children:[rb("Keywords  "),
          r("Quantum Key Distribution · Aurora protocol · Adaptive hybrid protocol · BB84 · SARG04 · "+
            "CHSH inequality · Entanglement verification · Real-time visualization · WebSocket · "+
            "GPU rendering · QFlux · Sifting efficiency · QBER · Post-processing · HCI · NASA-TLX")]
      }),

      // ══════════════════════════════════════════════════════════════════
      // 1. INTRODUCTION
      // ══════════════════════════════════════════════════════════════════
      sec("1  Introduction"),

      txt("Quantum Key Distribution (QKD) represents the most mature application of quantum information "+
          "science, offering cryptographic key exchange whose security is guaranteed by fundamental "+
          "physical laws rather than computational assumptions [1, 2]. Unlike classical public-key "+
          "cryptography — which relies on the assumed intractability of problems such as integer "+
          "factorization and discrete logarithms, and is therefore vulnerable to Shor's algorithm "+
          "running on future fault-tolerant quantum computers [3] — QKD exploits the no-cloning "+
          "theorem and measurement disturbance to detect eavesdropping with arbitrary reliability. "+
          "The BB84 protocol [1] and its entanglement-based counterpart E91 [2] established the "+
          "theoretical foundations; subsequent decades of research have produced protocols with "+
          "progressively stronger security proofs, higher key rates, and more practical hardware "+
          "requirements [4, 5]."),

      txt("Despite these advances, practical QKD implementations face a persistent fundamental "+
          "challenge: the trade-off between sifting efficiency and robustness against channel noise. "+
          "BB84 discards approximately 50% of transmitted photons during the sifting phase due to "+
          "basis mismatches — a waste that limits achievable key rates and increases the photon "+
          "budget required for a given key length. SARG04 [6] improves resistance to photon number "+
          "splitting (PNS) attacks with attenuated laser sources and achieves approximately 60% "+
          "sifting efficiency, but at the cost of a more complex reconciliation phase. Neither "+
          "protocol can dynamically adapt its operating mode in response to real-time channel "+
          "conditions: both apply a fixed strategy regardless of whether the channel is pristine "+
          "or severely degraded. In real-world deployments — where channel quality varies due to "+
          "atmospheric turbulence, mechanical vibration in fiber spools, and thermal polarization "+
          "drift — this rigidity means that protocols either sacrifice efficiency in clean channels "+
          "or compromise security in noisy ones."),

      txt("A second challenge is the absence of real-time monitoring tools capable of providing "+
          "continuous situational awareness of QKD channel health. Existing quantum simulation "+
          "platforms such as NetSquid [7] and SimulaQron [8] rely on batch processing, deferring "+
          "visualization until after simulation completion. This post-hoc paradigm imposes feedback "+
          "delays incompatible with interactive experimental parameter tuning. Classical infrastructure "+
          "monitoring tools such as Grafana [9] and Kibana [10] lack quantum-specific metric support "+
          "and cannot sustain the high-frequency update rates that quantum telemetry requires. "+
          "Standard Python visualization libraries are limited to 5–18 FPS by CPU-bound rendering "+
          "architectures — far below the ≥30 FPS needed for smooth real-time monitoring."),

      txt("This paper presents Aurora-QFlux, an integrated full-stack framework that addresses "+
          "both challenges simultaneously through two equally weighted contributions. The first "+
          "is Aurora, a novel adaptive hybrid QKD protocol that dynamically toggles between a "+
          "high-efficiency Efficient Mode and a secure Verified Mode based on real-time QBER "+
          "estimation, while continuously verifying channel integrity through CHSH entanglement "+
          "anchor checks. The second is QFlux, a GPU-accelerated real-time visualization dashboard "+
          "that streams quantum telemetry at sub-100 ms latency via asynchronous WebSocket "+
          "streaming and circular buffer memory management. Together, Aurora and QFlux form a "+
          "complete platform for quantum communication protocol research and operational monitoring."),

      sub("1.1  Principal Contributions"),
      txt("The principal contributions of this work are:"),
      bul("Aurora Protocol — a novel adaptive hybrid QKD protocol achieving 89.0%–93.8% sifting "+
          "efficiency and 2.45×–2.90× improvement in final secure key yield versus BB84, while "+
          "maintaining complete security with correct abort behavior at QBER ≥ 15%."),
      bul("CHSH Entanglement Anchor — a continuous entanglement verification mechanism using "+
          "5% of each transmission block to compute the CHSH S-value, providing eavesdropping "+
          "detection independent of QBER estimation."),
      bul("Adaptive Mode Switching — dynamic per-block toggling between Efficient Mode (paired-state "+
          "transmission with inconclusive-result rescue) and Verified Mode (BB84-equivalent), "+
          "triggered by QBER thresholds calibrated to maintain security while maximizing throughput."),
      bul("QFlux Dashboard — GPU-accelerated real-time visualization at 29.8 FPS / 42.4 ms mean "+
          "latency via PyQtGraph VBO rendering and asyncio WebSocket streaming with circular buffer "+
          "memory management (385 MB steady-state, session-duration independent)."),
      bul("Comprehensive Evaluation — 167 runs per (protocol, condition) combination across 5 QBER "+
          "levels and 5 distances (4,175 total simulation runs), with statistical analysis, efficiency "+
          "ratios, and improvement factors."),
      bul("Usability Validation — within-subjects HCI study (n = 12) demonstrating SUS = 82 (Excellent), "+
          "74% reduction in parameter tuning time, and 52% reduction in NASA-TLX cognitive workload."),
      ...gap(1),

      sub("1.2  Paper Organization"),
      txt("Section 2 provides background on QKD protocols and quantum channel modeling. Section 3 "+
          "presents the Aurora protocol in detail. Section 4 describes the QFlux system architecture. "+
          "Section 5 covers the implementation. Section 6 presents comprehensive experimental results "+
          "from the QBER sweep and distance sweep evaluations. Section 7 describes the QFlux usability "+
          "study. Section 8 provides discussion. Section 9 concludes the paper."),

      // ══════════════════════════════════════════════════════════════════
      // 2. BACKGROUND
      // ══════════════════════════════════════════════════════════════════
      sec("2  Background"),

      sub("2.1  Quantum Key Distribution Fundamentals"),
      txt("A QKD session between Alice (sender) and Bob (receiver) proceeds through four phases: "+
          "quantum transmission, sifting, error estimation, and post-processing (error correction "+
          "and privacy amplification) [4]. In the quantum transmission phase, Alice encodes classical "+
          "bits into quantum states — typically photon polarizations — and transmits them over the "+
          "quantum channel. Bob measures each received photon using a randomly chosen measurement basis. "+
          "The sifting phase retains only those bits where Alice and Bob used compatible bases, "+
          "discarding the remainder. Error estimation samples a fraction of sifted bits to compute "+
          "the quantum bit error rate (QBER) — the primary channel quality metric. If QBER exceeds "+
          "the protocol-specific security threshold, no secure key can be extracted and the session "+
          "must be aborted. The post-processing phase applies error correction to reconcile remaining "+
          "discrepancies and privacy amplification to eliminate any information an eavesdropper might "+
          "have gained, yielding the final secure key."),

      txt("The QBER reflects contributions from detector dark counts, photon loss, timing jitter, "+
          "polarization drift, and eavesdropping [11, 12]. For BB84 with standard error correction, "+
          "the security threshold is approximately QBER = 11%; above this level, the secure key "+
          "rate drops to zero. In fiber-based systems, attenuation increases exponentially with "+
          "distance, degrading signal-to-noise ratio and elevating QBER contributions from detector "+
          "dark counts. These physical constraints motivate the development of adaptive protocols "+
          "that can respond dynamically to channel conditions."),

      sub("2.2  BB84 Protocol"),
      txt("Proposed by Bennett and Brassard in 1984 [1], BB84 uses four quantum states spanning "+
          "two conjugate bases: the rectilinear basis {|0⟩, |1⟩} and the diagonal basis {|+⟩, |−⟩}. "+
          "Alice randomly selects a basis and bit value for each transmission; Bob randomly selects "+
          "a measurement basis. Approximately 50% of measurements use mismatched bases and are "+
          "discarded during sifting, yielding a sifting efficiency of approximately 50%. In our "+
          "experiments, BB84 achieves 50.1% sifting efficiency with a final secure key yield of "+
          "22.5% of raw bits at 2% QBER (225.0 ± 6.9 final bits per 1,000 raw bits). "+
          "BB84's security proof is information-theoretically complete [4], but its fixed 50% "+
          "sifting efficiency limits raw key throughput."),

      sub("2.3  SARG04 Protocol"),
      txt("Proposed by Scarani, Acín, Ribordy, and Gisin in 2004 [6], SARG04 uses the same four "+
          "quantum states as BB84 but modifies the classical sifting phase. Rather than Alice "+
          "announcing her basis, she announces a pair of non-orthogonal states. Bob can "+
          "conclusively determine the bit only if his measurement outcome eliminates one member "+
          "of the pair. This modification provides significantly stronger resistance to photon "+
          "number splitting (PNS) attacks when using weak coherent pulse (WCP) sources with "+
          "attenuated lasers — making SARG04 more practical for fiber-based implementations. "+
          "In our experiments, SARG04 achieves 60.1% sifting efficiency and 31.2% final key "+
          "yield at 2% QBER (312.3 ± 8.0 final bits per 1,000 raw bits), a 38.8% improvement "+
          "over BB84 in absolute final key yield. Both BB84 and SARG04 operate with fixed "+
          "strategies independent of channel conditions — the central limitation that Aurora addresses."),

      sub("2.4  The CHSH Inequality and Entanglement Verification"),
      txt("The Clauser-Horne-Shimony-Holt (CHSH) inequality [13] provides a device-independent "+
          "test for quantum entanglement. For a maximally entangled two-qubit state, the CHSH "+
          "S-value reaches S = 2√2 ≈ 2.828, exceeding the classical bound of S ≤ 2. Any "+
          "value S > 2 certifies genuine quantum correlations; S < 2 indicates that the "+
          "measurement statistics are compatible with a classical local hidden variable model, "+
          "suggesting channel compromise or eavesdropping. Aurora uses CHSH measurements on "+
          "a dedicated fraction of each transmission block as a continuous entanglement anchor, "+
          "providing an eavesdropping detection channel independent of QBER estimation."),

      sub("2.5  Related Work"),
      txt("Several adaptive QKD approaches have been proposed in the literature. Measurement-device-"+
          "independent QKD (MDI-QKD) [14] eliminates detector side channels but does not address "+
          "sifting efficiency. Twin-field QKD [15] extends the reach of fiber-based QKD through "+
          "single-photon interference but requires phase-stabilized links. Device-independent QKD "+
          "(DI-QKD) [16] offers the strongest security guarantees via loophole-free Bell tests "+
          "but requires near-perfect detectors impractical for current hardware. None of these "+
          "approaches implement dynamic per-block mode switching between a high-efficiency and "+
          "a high-security transmission mode based on real-time QBER estimation. Aurora "+
          "occupies a distinct niche: practical adaptive hybrid protocol implementable with "+
          "current QKD hardware operating in the prepare-and-measure regime."),

      // ══════════════════════════════════════════════════════════════════
      // 3. THE AURORA PROTOCOL
      // ══════════════════════════════════════════════════════════════════
      sec("3  The Aurora Protocol"),

      txt("Aurora is a novel adaptive hybrid QKD protocol designed to overcome the rigidity of "+
          "fixed-strategy protocols such as BB84 and SARG04. Its central innovation is the "+
          "combination of three mechanisms: a continuously monitored entanglement anchor for "+
          "eavesdropping detection, a high-efficiency Efficient Mode with inconclusive-result "+
          "rescue for clean channels, and a dynamic mode-switching algorithm that seamlessly "+
          "transitions between Efficient Mode and a secure Verified Mode in response to "+
          "real-time channel quality estimation. Figure 1 shows the Aurora protocol flow."),

      figBox("[Figure 1: Aurora protocol flow diagram — CHSH anchor check → mode selection (Efficient/Verified) → paired-state or BB84 transmission → rescue algorithm (EM only) → sifting → error correction → privacy amplification → secure key]"),
      fCap("Fig. 1  Aurora protocol operational flow. Each transmission block begins with CHSH anchor verification. Based on estimated QBER, the protocol selects Efficient Mode or Verified Mode for that block, processes the results (including rescue for inconclusive EM measurements), and forwards sifted bits to the post-processing pipeline."),

      sub("3.1  CHSH Entanglement Anchor Verification"),
      txt("At the beginning of each transmission block, Aurora dedicates a fraction p_anchor ≈ 5% "+
          "of photon pairs to CHSH inequality testing. Alice and Bob perform measurements in four "+
          "detector setting combinations (a, a') × (b, b') and compute the CHSH S-value:"),
      pC([rc("S = |E(a,b) − E(a,b') + E(a',b) + E(a',b')|",{size:20,italics:true})],
        {spacing:{before:80,after:80}}),
      txt("where E(x,y) is the correlation coefficient for setting pair (x,y). Under ideal conditions "+
          "with a maximally entangled source, S_ideal = 2√2 ≈ 2.828. Aurora applies a security "+
          "decision based on the computed S-value:"),
      bul("S ≥ 2.5: Channel is clean. Proceed with normal protocol operation."),
      bul("2.2 ≤ S < 2.5: Channel is degraded but usable. Switch to or remain in Verified Mode."),
      bul("S < 2.2: Channel is compromised (eavesdropping or severe hardware failure). Abort session immediately, discard all key material."),
      ...gap(1),
      txt("The CHSH anchor provides eavesdropping detection independent of QBER estimation, "+
          "guarding against intercept-resend attacks that maintain low QBER while compromising "+
          "security through partial information gain. This dual-channel security verification "+
          "is Aurora's primary security enhancement over standard prepare-and-measure protocols."),

      sub("3.2  Efficient Mode (EM): Paired-State Transmission with Rescue"),
      txt("When channel quality is high (estimated QBER < threshold_EM, default 6%), Aurora "+
          "operates in Efficient Mode. EM uses a paired-state transmission strategy in which "+
          "Alice transmits photons encoding one of four paired states selected to maximize the "+
          "probability of Bob obtaining a conclusive measurement outcome. Unlike BB84, which "+
          "discards all mismatched-basis measurements, EM distinguishes between:"),
      bul("Conclusive outcomes: Bob's measurement unambiguously identifies Alice's bit value. These are immediately incorporated into the sifted key."),
      bul("Inconclusive outcomes: Bob's measurement is ambiguous due to basis mismatch or noise. In standard protocols these are discarded; Aurora applies a Rescue Protocol."),
      ...gap(1),

      sub2("3.2.1  The Rescue Protocol"),
      txt("Aurora's Rescue Protocol applies a probabilistic recovery algorithm to a fraction of "+
          "inconclusive measurements. Using the statistical properties of the paired-state "+
          "encoding and Bob's measurement outcome distribution, the protocol computes a "+
          "posterior probability for Alice's bit value. If this posterior exceeds a configurable "+
          "confidence threshold (default: 0.85), the bit is tentatively included in the sifted "+
          "key with a flag for additional error correction scrutiny. The Rescue Protocol "+
          "is responsible for Aurora's sifting efficiency substantially exceeding the 50% "+
          "classical limit of BB84: at 2% QBER, Aurora achieves 89.0% sifting efficiency "+
          "(890.2 ± 6.5 sifted bits per 1,000 raw), rising to 93.8% at 11% QBER "+
          "(938.2 ± 2.9 sifted bits), as rescued inconclusive bits compensate for the increased "+
          "error rate in the conclusive pool."),

      sub("3.3  Verified Mode (VM): Secure Fallback"),
      txt("When channel quality degrades (estimated QBER ≥ threshold_EM, default 6%) or when "+
          "the CHSH S-value falls below 2.5, Aurora transitions to Verified Mode. VM implements "+
          "a standard BB84-equivalent prepare-and-measure protocol with basis reconciliation: "+
          "Alice announces her basis, Bob retains only matching-basis measurements, and "+
          "approximately 50% of bits are discarded during sifting. VM sacrifices the sifting "+
          "efficiency advantage of EM for the established, information-theoretically proven "+
          "security of BB84-like protocols. The transition from EM to VM is per-block and "+
          "instantaneous: within a single block, the protocol can switch modes without "+
          "interrupting the session."),

      sub("3.4  Adaptive Mode-Switching Logic"),
      txt("Aurora estimates the QBER for each transmission block using a sample of bits "+
          "whose values are publicly compared at the end of the block (the standard QKD "+
          "error estimation procedure). The mode-switching decision applies hysteresis to "+
          "prevent rapid oscillation between modes near the threshold boundary:"),
      bul("EM → VM transition: if estimated QBER > threshold_EM (default: 6%) for two consecutive blocks."),
      bul("VM → EM transition: if estimated QBER < threshold_VM (default: 3%) for three consecutive blocks."),
      bul("Session abort: if CHSH S-value < 2.2 for any block, regardless of QBER estimate."),
      ...gap(1),
      txt("The asymmetric hysteresis (2 blocks to switch to VM, 3 blocks to switch back to EM) "+
          "reflects the asymmetric cost of errors: a false EM→VM transition sacrifices efficiency "+
          "temporarily (recoverable), while a false VM→EM transition in a genuinely compromised "+
          "channel risks security (catastrophic). The default thresholds (6%/3%) were calibrated "+
          "through simulation sweeps to maximize final key yield across the tested QBER range "+
          "while maintaining correct security behavior at the 11% and 15% boundary conditions."),

      sub("3.5  Post-Processing Pipeline"),
      txt("Both EM and VM outputs pass through Aurora's unified post-processing pipeline:"),
      bul("Error Correction: Identifies and reconciles mismatched bits between Alice and Bob "+
          "using a Cascade-style protocol [17]. For EM, rescued bits receive additional parity "+
          "check passes due to their lower posterior confidence. Error correction overhead "+
          "increases with QBER: at 2% QBER, error correction retains the majority of sifted "+
          "bits; at 11% QBER, a larger fraction is discarded."),
      bul("Privacy Amplification: Applies a universal hash function to the error-corrected "+
          "key to eliminate any partial information an eavesdropper might have gained. "+
          "The compression factor is computed from the estimated QBER and error correction "+
          "information leakage. At QBER ≥ 15%, the compression factor reaches 1.0 "+
          "(complete discard), yielding zero final key bits and correctly setting "+
          "security_passed = False for all protocols."),
      ...gap(1),

      sub("3.6  Security Analysis"),
      txt("Aurora's security rests on two independent pillars. First, the Verified Mode implements "+
          "standard BB84-equivalent security — any session block processed in VM inherits "+
          "BB84's unconditional security proof [4]. Second, the CHSH entanglement anchor "+
          "provides device-independent eavesdropping detection for the anchor fraction of "+
          "each block: a CHSH S-value significantly above the classical bound (S > 2) "+
          "certifies that the anchor photon pairs have not been intercepted, as interception "+
          "would collapse the entangled state and suppress the CHSH violation."),
      txt("The Efficient Mode carries a security caveat: the Rescue Protocol's probabilistic "+
          "bit recovery introduces a small additional error rate in rescued bits, which is "+
          "bounded by the confidence threshold. At confidence threshold 0.85, the maximum "+
          "additional bit error rate from rescued bits is 15%, which is accounted for in "+
          "the error correction and privacy amplification steps. The effective QBER seen "+
          "by post-processing includes both transmission errors and rescue errors, ensuring "+
          "that privacy amplification correctly accounts for any information leakage."),

      // ══════════════════════════════════════════════════════════════════
      // 4. QFLUX SYSTEM ARCHITECTURE
      // ══════════════════════════════════════════════════════════════════
      sec("4  QFlux System Architecture"),

      txt("QFlux is a three-layer real-time visualization dashboard designed to provide "+
          "continuous monitoring of QKD simulation telemetry. Its architecture enforces "+
          "strict separation between simulation, communication, and visualization concerns, "+
          "preventing cross-layer performance coupling. Figure 2 shows the overall architecture."),

      figBox("[Figure 2: QFlux three-layer architecture — Layer 1: QKD Simulation Backend (Aurora/BB84/SARG04 simulator + noise model + telemetry generator) → Layer 2: asyncio WebSocket server (port 8080) → Layer 3: PyQt5 GUI + PyQtGraph VBO renderer + circular buffers]"),
      fCap("Fig. 2  QFlux three-layer architecture. The simulation backend runs as an independent subprocess. The asyncio WebSocket layer streams telemetry asynchronously. The visualization frontend uses GPU-accelerated PyQtGraph rendering with circular buffer memory management."),

      sub("4.1  Layer 1 — Simulation Backend"),
      txt("The simulation backend implements BB84, SARG04, and Aurora as independent protocol "+
          "modules within a unified simulation engine. The backend runs as an OS subprocess "+
          "(Python multiprocessing) to bypass the GIL and allow simulation and rendering to "+
          "utilize independent CPU cores. The quantum channel model simulates fiber attenuation "+
          "T = 10^(−αL/10) (α = 0.2 dB/km), detector efficiency η, dark count rate d_c, "+
          "and timing jitter σ_t. At each simulation step, the telemetry generator samples "+
          "protocol state and constructs a JSON telemetry packet (mean size: 220 bytes) "+
          "containing: timestamp, protocol, QBER, raw/sifted/final key lengths, "+
          "execution time, security_passed flag, and (for Aurora) current mode (EM/VM) "+
          "and CHSH S-value."),

      sub("4.2  Layer 2 — WebSocket Communication"),
      txt("The communication layer is an asyncio-based WebSocket server (websockets v11.0.3) "+
          "on ws://localhost:8080/ws. Full-duplex WebSocket enables bidirectional operation: "+
          "the server streams telemetry to the visualization frontend, and the frontend "+
          "transmits parameter update commands (attenuation, QBER, protocol selection) "+
          "back to the simulation backend. Asyncio's cooperative scheduling provides "+
          "backpressure isolation: a temporarily slow rendering cycle cannot stall simulation "+
          "throughput or corrupt the telemetry timeline."),

      sub("4.3  Layer 3 — Visualization Frontend"),
      txt("The visualization frontend is built on PyQt5 (v5.15.9) with PyQtGraph (v0.13.3) "+
          "for GPU-accelerated rendering via OpenGL Vertex Buffer Objects (VBOs). "+
          "Three concurrent contexts operate: the Qt main thread (GUI, QTimer-triggered "+
          "rendering), a WebSocket client coroutine (asyncio, packet deserialisation, "+
          "circular buffer writes), and per-channel circular buffers (N = 3,000 samples, "+
          "O(1) insertion, O(N) rendering). The dashboard displays six real-time metric "+
          "panels: QBER, photon detection rate, raw/sifted/final key rates, and "+
          "execution time. For Aurora, an additional panel shows the current mode "+
          "(EM/VM) and CHSH S-value. Color-coded QBER alert overlays fire at "+
          "configurable thresholds (default: orange ≥ 8%, red ≥ 11%)."),

      sub("4.4  Rendering Optimization"),
      txt("QFlux achieves consistent 30 Hz rendering through three complementary mechanisms. "+
          "First, circular buffer memory management maintains O(N) rendering complexity "+
          "regardless of session duration, stabilizing RSS at 385 ± 4 MB after an initial "+
          "90-second warm-up versus 1.9 GB after one hour for naive list accumulation. "+
          "Second, adaptive stride-based downsampling with stride K = ⌊f_sim / f_render⌋ "+
          "decouples simulation throughput from rendering load without perceptible quality loss. "+
          "Third, PyQtGraph's OpenGL VBO rendering offloads pixel-fill computation to the GPU, "+
          "achieving 29.8 FPS at 30 Hz input with 4.1% CPU utilization — a 3.6× frame-rate "+
          "improvement over Matplotlib (8.2 FPS, 42% CPU)."),

      // ══════════════════════════════════════════════════════════════════
      // 5. IMPLEMENTATION
      // ══════════════════════════════════════════════════════════════════
      sec("5  Implementation"),

      sub("5.1  Technology Stack"),

      tCap("Table 1  Aurora-QFlux implementation stack"),
      mkT(
        ["Component","Library / Technology","Version","Role"],
        [
          ["Protocol simulation","Python","3.11","BB84, SARG04, Aurora protocol engines"],
          ["Backend API","FastAPI","0.110","REST endpoints + WebSocket server (ws://localhost:8080/ws)"],
          ["WebSocket","websockets","11.0.3","Async full-duplex telemetry streaming"],
          ["GUI framework","PyQt5","5.15.9","Window management, QTimer, widget hosting"],
          ["Visualization","PyQtGraph","0.13.3","GPU-accelerated OpenGL VBO rendering"],
          ["Async runtime","asyncio (stdlib)","3.11","Coroutine scheduling, backpressure isolation"],
          ["Subprocess","multiprocessing","3.11","Simulation process isolation (GIL bypass)"],
          ["Numerics","NumPy","1.25.2","Circular buffers, stride downsampling, CHSH computation"],
          ["Data export","csv / pandas","stdlib / 2.0","CSV export, PDF report generation"],
        ],
        [1600,1800,1100,3138]
      ),
      ...gap(1),

      sub("5.2  Protocol Engine Design"),
      txt("Each protocol (BB84, SARG04, Aurora) is implemented as a Python class inheriting "+
          "from a common QKDProtocol base class that defines the interface for quantum "+
          "transmission, sifting, error estimation, error correction, and privacy amplification. "+
          "This design enables the simulation frontend to switch between protocols without "+
          "restarting the backend. Aurora's mode-switching logic is encapsulated in an "+
          "AdaptiveController class that maintains per-block QBER history, CHSH S-value "+
          "history, and the current mode state (EM/VM). The controller's switching decisions "+
          "are logged to the telemetry stream, enabling real-time visualization of mode "+
          "transitions in the QFlux dashboard."),

      sub("5.3  Dashboard and Data Export"),
      txt("The QFlux dashboard provides a glassmorphism-styled interface with real-time "+
          "dynamic charts for all six telemetry metrics plus Aurora's mode indicator panel. "+
          "Three data export facilities are supported: CSV export of the circular buffer "+
          "contents (timestamped per-run metric values), chart PNG export (current dashboard "+
          "state as a high-resolution image), and PDF report generation (structured summary "+
          "of the session including protocol comparison statistics). All exports are triggered "+
          "from the dashboard without interrupting live monitoring."),

      // ══════════════════════════════════════════════════════════════════
      // 6. EXPERIMENTAL EVALUATION
      // ══════════════════════════════════════════════════════════════════
      sec("6  Experimental Evaluation"),

      txt("We conducted comprehensive experimental evaluation of the three protocols across "+
          "two systematic sweeps: a QBER sweep varying channel noise from 2% to 15% at fixed "+
          "distance (20 km), and a distance sweep varying channel distance from 5 km to 50 km "+
          "at fixed QBER (2%). Each (protocol, condition) combination was evaluated over "+
          "n = 167 independent simulation runs with 1,000 raw bits per run, yielding "+
          "3 protocols × 5 conditions × 167 runs = 2,505 runs per sweep and 5,010 total runs. "+
          "All runs were executed on a consistent hardware platform. Statistical summaries "+
          "report mean ± standard deviation across the 167 runs."),

      sub("6.1  QBER Sweep: Impact of Channel Noise on Key Generation"),

      sub2("6.1.1  Sifting Efficiency"),
      txt("Table 2 presents sifting efficiency (sifted key / raw key × 100%) across "+
          "all protocols and QBER levels. Aurora's sifting efficiency is 89.0%–93.8% across "+
          "all tested noise levels — a 1.78×–1.88× improvement over BB84 (≈50%) and "+
          "1.48×–1.56× over SARG04 (≈60%). Notably, Aurora's sifting efficiency "+
          "increases with QBER (89.0% at 2% → 93.8% at 11%), as the Rescue Protocol "+
          "recovers an increasing fraction of inconclusive measurements to compensate for "+
          "the reduced conclusive-outcome yield at higher error rates. At QBER = 15%, "+
          "Aurora correctly produces 0 sifted bits (CHSH abort), in contrast to BB84 "+
          "and SARG04 which continue sifting but produce 0 final key bits (security_passed = False)."),

      tCap("Table 2  Sifting efficiency (%) across protocols and QBER levels (n = 167 runs per cell, mean ± SD)"),
      mkT(
        ["QBER","BB84 Sifted (%)","SARG04 Sifted (%)","Aurora Sifted (%)","Aurora / BB84"],
        [
          ["2%",  "50.1 ± 1.5", "60.1 ± 1.5", "89.0 ± 0.7", "1.78×"],
          ["5%",  "50.0 ± 1.6", "60.3 ± 1.6", "90.6 ± 2.2", "1.81×"],
          ["8%",  "50.0 ± 1.7", "60.1 ± 1.6", "93.5 ± 0.9", "1.87×"],
          ["11%", "49.9 ± 1.5", "60.2 ± 1.5", "93.8 ± 0.3", "1.88×"],
          ["15%", "49.9 ± 1.6", "60.0 ± 1.5", "0.0 (abort)", "—"],
        ],
        [1000,1800,1800,1800,1238]
      ),
      ...gap(1),

      sub2("6.1.2  Final Secure Key Yield"),
      txt("Table 3 presents final secure key length (bits per 1,000 raw bits) and improvement "+
          "factors. Aurora outperforms BB84 by 2.45× at 2% QBER, increasing to 2.90× at 11% QBER "+
          "— the improvement factor grows with noise because Aurora's adaptive mode switching "+
          "maintains higher sifting efficiency while BB84's fixed strategy sees accelerating "+
          "privacy amplification compression. At 2% QBER, Aurora produces 551.5 final bits "+
          "versus BB84's 225.0 and SARG04's 312.3 — the latter representing a 76.5% improvement "+
          "over BB84 but still 43.5% short of Aurora. At 11% QBER, Aurora produces 454.4 final "+
          "bits versus BB84's 156.8 (a 189.9% improvement) and SARG04's 231.1. "+
          "At QBER = 15%, all three protocols produce 0 final bits, confirming correct security "+
          "termination."),

      tCap("Table 3  Final secure key yield (bits / 1000 raw bits) and improvement factors (n = 167, mean ± SD)"),
      mkT(
        ["QBER","BB84 Final","SARG04 Final","Aurora Final","Aurora/BB84","Aurora/SARG04"],
        [
          ["2%",  "225.0 ± 6.9",  "312.3 ± 8.0",  "551.5 ± 4.1",  "2.45×", "1.77×"],
          ["5%",  "202.1 ± 6.3",  "285.8 ± 7.7",  "520.4 ± 12.7", "2.57×", "1.82×"],
          ["8%",  "179.6 ± 6.2",  "257.7 ± 6.9",  "495.2 ± 4.8",  "2.76×", "1.92×"],
          ["11%", "156.8 ± 4.8",  "231.1 ± 5.9",  "454.4 ± 1.4",  "2.90×", "1.97×"],
          ["15%", "0 (sec fail)", "0 (sec fail)", "0 (abort)",     "—",     "—"],
        ],
        [850,1500,1500,1500,1120,1168]
      ),
      ...gap(1),

      figBox("[Figure 3: Line chart — Final key length (bits) vs. QBER for BB84, SARG04, Aurora. Y-axis: 0–600 bits. X-axis: 2%, 5%, 8%, 11%, 15%. Three lines with error bars (±1 SD). Aurora line consistently highest; all converge to 0 at 15%.]"),
      fCap("Fig. 3  Final secure key yield versus channel QBER for all three protocols. Error bars represent ±1 standard deviation across 167 runs. Aurora consistently dominates; all protocols correctly yield 0 bits at QBER = 15%."),

      sub2("6.1.3  Security Pass Rate"),
      txt("All 167 runs per (protocol, QBER) combination pass the security check (security_passed = True) "+
          "for QBER ∈ {2%, 5%, 8%, 11%}. At QBER = 15%, all 167 runs per protocol correctly "+
          "fail the security check (security_passed = False for BB84 and SARG04; CHSH abort "+
          "for Aurora), yielding a 100% security pass rate at valid QBER levels and "+
          "100% correct abort rate at the security boundary. This confirms that all three "+
          "protocol implementations correctly enforce security termination."),

      sub2("6.1.4  Execution Time and Computational Overhead"),
      txt("Table 4 presents mean execution time per 1,000-bit simulation run. BB84 executes "+
          "fastest at 14.88 ms (2% QBER), reflecting its simple basis-comparison sifting. "+
          "SARG04 requires 24.54 ms due to its more complex pair-announcement reconciliation. "+
          "Aurora requires 65.54 ms — a 4.40× overhead versus BB84 — attributable to "+
          "the CHSH anchor computation (requiring 4 correlation coefficient calculations per block), "+
          "the paired-state posterior computation, and the Rescue Protocol's iterative "+
          "confidence evaluation. Execution time decreases slightly with increasing QBER for "+
          "all protocols, as higher error rates reduce post-processing work (fewer bits "+
          "survive to privacy amplification)."),

      tCap("Table 4  Mean execution time per 1,000-bit run (ms, mean ± SD, n = 167)"),
      mkT(
        ["QBER","BB84 (ms)","SARG04 (ms)","Aurora (ms)","Aurora / BB84 overhead"],
        [
          ["2%",  "14.88 ± 1.60", "24.54 ± 1.54", "65.54 ± 2.90", "4.40×"],
          ["5%",  "13.14 ± 1.01", "22.49 ± 1.32", "62.42 ± 3.25", "4.75×"],
          ["8%",  "11.86 ± 1.30", "20.39 ± 1.39", "61.27 ± 2.11", "5.17×"],
          ["11%", "10.47 ± 1.75", "18.23 ± 1.01", "55.97 ± 0.74", "5.35×"],
          ["15%", " 8.39 ± 0.54", "15.63 ± 1.21", "0.00 (abort)", "—"],
        ],
        [900,1550,1550,1550,1688]
      ),
      ...gap(1),

      txt("The computational overhead of Aurora (4.40×–5.35× over BB84) represents the "+
          "quantifiable cost of its security and efficiency advantages. Given that Aurora "+
          "produces 2.45×–2.90× more final key bits, the effective computation per "+
          "final-key-bit ratio is substantially more favorable: Aurora requires "+
          "approximately 65.54 / 551.5 = 0.119 ms per final key bit versus "+
          "14.88 / 225.0 = 0.066 ms for BB84 — a 1.80× overhead per final key bit, "+
          "compared to the 4.40× headline execution time ratio. This context "+
          "demonstrates that Aurora's computational cost, while real, is partially "+
          "amortized by its higher key yield."),

      sub("6.2  Distance Sweep: Algorithmic Stability Under Attenuation"),
      txt("The distance sweep evaluates all three protocols at fixed QBER = 2% across "+
          "channel distances of 5, 10, 20, 35, and 50 km. As discussed in Section 2, "+
          "the simulator fixes the raw key length at 1,000 bits per run (representing "+
          "controlled algorithmic analysis), while noting that in physical deployments, "+
          "distance would exponentially reduce the raw key generation rate via "+
          "T = 10^(−αL/10) attenuation."),

      tCap("Table 5  Distance sweep results at QBER = 2% (n = 167 runs per cell, mean ± SD)"),
      mkT(
        ["Distance (km)","BB84 Final (bits)","SARG04 Final (bits)","Aurora Final (bits)","Exec Time: Aurora (ms)"],
        [
          ["5",  "224.4 ± 6.8", "311.7 ± 7.9", "551.7 ± 4.2", "65.73 ± 3.11"],
          ["10", "224.6 ± 7.0", "311.1 ± 7.8", "552.5 ± 4.0", "65.38 ± 3.05"],
          ["20", "223.7 ± 6.9", "311.1 ± 7.8", "552.7 ± 4.1", "65.66 ± 3.18"],
          ["35", "224.3 ± 6.8", "310.5 ± 7.7", "552.7 ± 4.1", "68.83 ± 3.42"],
          ["50", "224.4 ± 6.8", "311.3 ± 7.8", "552.4 ± 4.2", "65.70 ± 3.09"],
        ],
        [1250,1750,1750,1750,1138]
      ),
      ...gap(1),

      txt("The final key length standard deviation across all five distances is 0.3 bits "+
          "for BB84, 0.4 bits for SARG04, and 0.4 bits for Aurora — effectively zero "+
          "variation. This extreme stability (coefficient of variation < 0.2%) confirms "+
          "that within the simulator's algorithmic model, protocol performance is "+
          "determined entirely by QBER and not by distance, which only affects the "+
          "physical raw key generation rate. Aurora's execution time shows a slight "+
          "elevation at 35 km (68.83 ms vs. 65–66 ms at other distances), attributable "+
          "to OS scheduler variance rather than algorithmic distance dependence "+
          "(the difference is within 1.5 standard deviations and not statistically significant)."),

      figBox("[Figure 4: Bar chart — Final key length (bits) at 5 distances for all 3 protocols. Grouped bars. Aurora consistently ~552 bits, SARG04 ~311 bits, BB84 ~224 bits. Error bars ±1 SD. Y-axis: 0–620 bits.]"),
      fCap("Fig. 4  Final secure key length versus channel distance (QBER = 2%). All three protocols exhibit near-zero variation across 5–50 km, confirming algorithmic distance stability. Aurora maintains a consistent 2.46× advantage over BB84."),

      sub("6.3  Protocol Comparison Summary"),
      txt("Table 6 consolidates the key performance metrics for all three protocols at the "+
          "primary evaluation condition (QBER = 2%, distance = 20 km):"),

      tCap("Table 6  Protocol comparison summary at QBER = 2%, distance = 20 km"),
      mkT(
        ["Metric","BB84","SARG04","Aurora","Aurora vs BB84"],
        [
          ["Sifting efficiency",     "50.1%",    "60.1%",    "89.0%",         "+77.6%"],
          ["Final key yield (bits)", "225.0±6.9","312.3±8.0","551.5±4.1",     "+145.1% (2.45×)"],
          ["Final key yield (%)",    "22.5%",    "31.2%",    "55.2%",         "+32.7 pp"],
          ["Execution time (ms)",    "14.88",    "24.54",    "65.54",         "4.40× slower"],
          ["Compute per key bit",    "0.066 ms/b","0.079 ms/b","0.119 ms/b", "1.80× slower"],
          ["Security @ 15% QBER",   "Fail (0b)","Fail (0b)","Abort (0b)",    "Equivalent"],
          ["PNS attack resistance",  "Standard", "Enhanced", "CHSH-verified", "Superior"],
        ],
        [1950,1300,1300,1300,1388]
      ),
      ...gap(1),

      // ══════════════════════════════════════════════════════════════════
      // 7. QFLUX USABILITY STUDY
      // ══════════════════════════════════════════════════════════════════
      sec("7  QFlux Usability Study"),

      sub("7.1  Study Design"),
      txt("We conducted a controlled within-subjects experiment comparing QFlux against "+
          "a Matplotlib-based batch-processing baseline representing current standard "+
          "practice in quantum communication simulation workflows. Twelve graduate researchers "+
          "(7 male, 5 female; mean age 24.3 ± 1.8 years) enrolled in quantum communication "+
          "or quantum networking courses participated. Each completed two sessions in "+
          "counterbalanced order separated by a 48-hour washout period. All sessions used "+
          "Aurora-QFlux with the Aurora protocol active, providing the most complex "+
          "telemetry stream (mode switching, CHSH values, and all six standard metrics)."),

      sub("7.2  Tasks"),
      bul("T1 — Anomaly Detection: identify the time at which QBER first exceeds 10% during a 5-minute pre-recorded run (accuracy within ±5 seconds)."),
      bul("T2 — Parameter Tuning: adjust attenuation and QBER parameters to drive Aurora below the EM→VM threshold (QBER < 3%) and maintain Efficient Mode for a continuous 2-minute window within 10 minutes."),
      bul("T3 — Comparative Analysis: identify qualitative differences in QBER evolution and mode-switching patterns between two simultaneous Aurora simulation channels."),
      ...gap(1),

      sub("7.3  Measures"),
      txt("Task completion time (minutes), NASA-TLX composite workload score (0–100), "+
          "and System Usability Scale (SUS) score (0–100). Statistical significance "+
          "assessed via paired Wilcoxon signed-rank test with Bonferroni correction "+
          "(α_corrected = 0.002); effect sizes via Cohen's d for paired samples."),

      sub("7.4  Results"),

      tCap("Table 7  QFlux usability study results (mean ± SD, n = 12, all p < 0.001 after Bonferroni correction)"),
      mkT(
        ["Measure","Baseline (Matplotlib)","QFlux","Change","Cohen's d"],
        [
          ["T1 Anomaly detection (min)", "8.3 ± 1.8",  "2.1 ± 0.4",  "−74.7%", "4.6"],
          ["T2 Parameter tuning (min)",  "12.5 ± 2.1", "3.2 ± 0.7",  "−74.4%", "5.3"],
          ["T3 Comparison (min)",        "15.2 ± 3.0", "5.8 ± 1.1",  "−61.8%", "4.1"],
          ["NASA-TLX composite",         "68.4 ± 7.3", "32.8 ± 5.1", "−52.0%", "5.7"],
          ["SUS score",                  "51.2 ± 8.4", "82.0 ± 6.2", "+60.2%", "4.2"],
        ],
        [2200,1700,1500,1100,1138]
      ),
      ...gap(1),

      txt("The QFlux SUS score of 82.0 meets the Excellent threshold (> 80.3) [18]. "+
          "All effect sizes exceed d = 4.0, indicating the QFlux advantage is not a "+
          "marginal usability improvement but a categorical difference in interaction "+
          "paradigm. Post-session qualitative feedback identified three most-valued features: "+
          "continuous live QBER trace (11/12 participants), color-coded QBER threshold "+
          "alerts (10/12), and the Aurora mode indicator panel showing EM/VM transitions "+
          "in real time (9/12). The mode indicator panel was specific to the Aurora protocol "+
          "and not available in the conference version; it was cited as enabling researchers "+
          "to observe Aurora's adaptive behavior directly rather than inferring it from "+
          "post-hoc log files."),

      sub("7.5  QFlux Rendering Performance"),
      tCap("Table 8  QFlux rendering performance versus baseline visualization frameworks"),
      mkT(
        ["Framework","Input (Hz)","FPS","CPU (%)","Latency mean (ms)","Memory (MB, 1hr)"],
        [
          ["Matplotlib (baseline)", "30", "8.2",  "42",  "N/A",  ">1900"],
          ["Plotly Dash",           "30", "14.3", "31",  "N/A",  "N/A"],
          ["QFlux (PyQtGraph)",     "30", "29.8", "4.1", "42.4", "385 ± 4"],
          ["QFlux (PyQtGraph)",     "60", "45.0", "5.3", "N/A",  "385 ± 4"],
        ],
        [1900,1000,900,1000,1500,1338]
      ),
      ...gap(1),

      // ══════════════════════════════════════════════════════════════════
      // 8. DISCUSSION
      // ══════════════════════════════════════════════════════════════════
      sec("8  Discussion"),

      sub("8.1  Aurora's Efficiency-Security Trade-off"),
      txt("The experimental results confirm Aurora's central design hypothesis: dynamic "+
          "mode switching enables sifting efficiency substantially exceeding the classical "+
          "BB84 limit while maintaining complete security. The 89.0%–93.8% sifting efficiency "+
          "range represents a near-doubling of the ~50% BB84 efficiency, and the 2.45×–2.90× "+
          "improvement in final secure key yield demonstrates that this sifting advantage "+
          "survives post-processing. The growing improvement factor with QBER "+
          "(2.45× at 2% → 2.90× at 11%) is a particularly noteworthy finding: Aurora's "+
          "advantage is largest precisely when channel conditions are most challenging, "+
          "when maximum key yield is most operationally important."),

      txt("The 4.40× computational overhead versus BB84 is the primary practical limitation "+
          "of Aurora. For software simulation environments — which represent Aurora's "+
          "primary near-term deployment context — this overhead is acceptable: 65 ms per "+
          "1,000-bit simulation run implies that a 1 Mbps simulation session would require "+
          "approximately 65 seconds of compute time per simulated second, feasible on "+
          "modern multi-core workstations with multiple simulation subprocesses. "+
          "For hardware QKD implementations, the CHSH anchor computation and Rescue "+
          "Protocol would need to be implemented in FPGA or ASIC logic to achieve "+
          "real-time throughput — identified as priority hardware integration work."),

      sub("8.2  The Rescue Protocol's Role"),
      txt("The monotonically increasing sifting efficiency with QBER (89.0% at 2% → 93.8% "+
          "at 11%) reveals an important property of the Rescue Protocol: at higher QBER, "+
          "more measurements fall into the inconclusive category, and the Rescue Protocol "+
          "recovers a larger absolute number of bits. This partially compensates for the "+
          "reduction in conclusive-outcome yield, resulting in counterintuitively higher "+
          "sifting efficiency at higher noise. The final key trend is the net result of "+
          "this sifting efficiency increase partially offsetting the increasing privacy "+
          "amplification compression at higher QBER: final keys decline from 551.5 to "+
          "454.4 bits (17.6% reduction) as QBER increases from 2% to 11%, compared to "+
          "a 30.3% reduction for BB84 (225.0 to 156.8 bits). Aurora's final key is "+
          "therefore more noise-resilient than BB84's."),

      sub("8.3  Distance Stability and Physical Mapping"),
      txt("The near-zero variation in final key yield across 5–50 km (std dev < 0.4 bits) "+
          "confirms that the simulator correctly isolates the algorithmic component of "+
          "protocol performance from physical channel attenuation effects. In real "+
          "physical deployments, the 1,000-bit raw key would require exponentially "+
          "more photon transmission time at longer distances: at α = 0.2 dB/km, "+
          "a 50 km link has channel transmissivity T = 10^(−0.2×50/10) = 10^(−1) = 10%, "+
          "meaning Alice must transmit approximately 10× more photon pulses to collect "+
          "1,000 detected photons at Bob. This physical effect — longer key accumulation "+
          "time — is independent of the algorithmic post-processing results demonstrated here "+
          "and would affect all three protocols equally."),

      sub("8.4  QFlux as an Operational Research Platform"),
      txt("The usability study results demonstrate that QFlux's real-time visualization "+
          "transforms Aurora parameter tuning from a 12.5-minute batch-process-inspect "+
          "cycle to a 3.2-minute interactive process — a 4× throughput increase per "+
          "experimental iteration. For Aurora specifically, the mode indicator panel "+
          "and CHSH S-value display provide capabilities unavailable in any batch "+
          "visualization tool: researchers can observe the protocol's adaptive behavior "+
          "as it occurs, correlating mode switches with QBER transients in real time. "+
          "This capability is essential for calibrating Aurora's mode-switching thresholds "+
          "for specific deployment conditions."),

      sub("8.5  Limitations"),
      txt("Three primary limitations warrant acknowledgment. First, Aurora's security "+
          "proof for the Efficient Mode is not yet information-theoretically complete. "+
          "The Rescue Protocol's probabilistic bit recovery introduces assumptions about "+
          "the posterior distribution of Alice's bit value that require formal security "+
          "analysis — particularly for adversarial scenarios where Eve controls the noise "+
          "distribution. A full composable security proof for Aurora is identified as the "+
          "highest-priority theoretical follow-up."),
      txt("Second, both Aurora and QFlux have been evaluated using simulated quantum channel "+
          "telemetry. Hardware integration with commercial QKD platforms (ID Quantique "+
          "Clavis³, Toshiba QKD appliance) is needed to validate end-to-end system "+
          "performance under realistic physical-layer conditions including laser intensity "+
          "fluctuations, detector after-pulsing, and clock synchronization errors."),
      txt("Third, the usability study sample (n = 12) limits generalizability. "+
          "A larger study spanning diverse expertise levels and institutional contexts "+
          "is needed to confirm the observed effect sizes."),

      sub("8.6  Future Work"),
      bul("Formal security proof for Aurora's Efficient Mode under composable security framework."),
      bul("FPGA implementation of the CHSH anchor computation and Rescue Protocol for real-time hardware QKD integration."),
      bul("Integration with NetSquid event-driven API for Aurora simulation at network scale (multi-node quantum networks [19])."),
      bul("Machine-learning-based adaptive threshold calibration: replacing fixed EM/VM thresholds with a learned policy trained on historical QBER distributions for a given deployment environment [20]."),
      bul("Web-based QFlux frontend (WebGL rendering) for platform-independent remote monitoring of deployed QKD networks."),
      bul("Extended usability study (n ≥ 30) spanning diverse expertise levels, institutional contexts, and operating systems."),
      ...gap(1),

      // ══════════════════════════════════════════════════════════════════
      // 9. CONCLUSION
      // ══════════════════════════════════════════════════════════════════
      sec("9  Conclusion"),

      txt("This paper has presented Aurora-QFlux, an integrated full-stack framework combining "+
          "a novel adaptive QKD protocol with a GPU-accelerated real-time visualization dashboard. "+
          "Aurora addresses the fundamental rigidity of fixed-strategy QKD protocols by "+
          "dynamically selecting between a high-efficiency Efficient Mode with inconclusive-result "+
          "rescue and a secure Verified Mode with BB84-equivalent security guarantees, guided by "+
          "real-time per-block QBER estimation and continuous CHSH entanglement anchor verification."),

      txt("Experimental evaluation across 5,010 simulation runs demonstrates that Aurora "+
          "achieves 89.0%–93.8% sifting efficiency — nearly doubling BB84's 50.1% — and "+
          "produces 2.45×–2.90× more final secure key bits across all tested noise levels "+
          "(QBER 2%–11%), with the efficiency advantage growing as channel conditions "+
          "deteriorate. At QBER = 15%, all protocols correctly terminate with zero key output, "+
          "confirming correct security boundary enforcement. Distance sweep experiments "+
          "confirm algorithmic stability with final key standard deviation below 0.4 bits "+
          "across 5–50 km. Aurora's 4.40× computational overhead versus BB84 is partially "+
          "amortized by its higher key yield, resulting in a 1.80× overhead per final key bit."),

      txt("QFlux delivers continuous telemetry visualization at 29.8 FPS and 42.4 ms mean "+
          "end-to-end latency, satisfying the sub-100 ms real-time responsiveness criterion "+
          "at the 99th percentile. Circular buffer memory management bounds session RSS at "+
          "385 MB independent of duration. A controlled usability study (n = 12) yields "+
          "SUS = 82 (Excellent), 74% reduction in parameter tuning time, and 52% reduction "+
          "in NASA-TLX cognitive workload (all p < 0.001, Cohen's d > 4.0), confirming "+
          "that real-time visualization categorically transforms the quantum communication "+
          "research workflow."),

      txt("Aurora-QFlux is implemented entirely in Python 3.11 with standard open-source "+
          "libraries, ensuring broad accessibility. Its modular architecture enables "+
          "independent extension of the protocol engine, communication layer, and "+
          "visualization frontend. Source code and experimental data will be released "+
          "as open-source upon acceptance of this manuscript. Aurora-QFlux provides the "+
          "quantum communication community with a unified platform for adaptive protocol "+
          "research and operational QKD network monitoring."),

      // ══════════════════════════════════════════════════════════════════
      // DECLARATIONS
      // ══════════════════════════════════════════════════════════════════
      sec("Declarations"),

      p([rb("Ethical Approval  "),r("The usability study was conducted with informed consent from all twelve participants. "+
        "No personally identifiable data were collected. The study protocol was reviewed and approved by "+
        "the Institutional Review Board of Amrita Vishwa Vidyapeetham, Mysuru "+
        "(Protocol No.: [insert IRB reference before submission]).")]),

      p([rb("Consent for Publication  "),r("All authors consent to publication of this manuscript.")]),

      p([rb("Availability of Data and Materials  "),r("The Aurora-QFlux source code, simulation datasets "+
        "(distance_sweep_runs.csv, qber_sweep_runs.csv), and anonymized usability study data are available "+
        "from the corresponding author upon reasonable request. The authors intend to release the "+
        "source code as an open-source GitHub repository and the datasets as supplementary files upon acceptance.")]),

      p([rb("Patent Disclosure  "),r("A university patent application covering aspects of the Aurora adaptive "+
        "QKD protocol has been filed with Amrita Vishwa Vidyapeetham (Application C102: "+
        "'A System and Method of Adaptive Quantum Key Distribution'). The present journal paper "+
        "describes the simulation and visualization framework (Aurora-QFlux) in the context of "+
        "the Aurora protocol. Patent applicants include Adwitiya Mukhopadhyay, Saadhan P, and Rashmitha S.")]),

      p([rb("Competing Interests  "),r("The authors declare no competing interests. No funding was received "+
        "from commercial entities with interests in quantum communication technologies.")]),

      p([rb("Funding  "),r("This research received no specific grant from any funding agency in the public, "+
        "commercial, or not-for-profit sectors. The open-access publication fee is covered by the "+
        "institutional agreement between Amrita Vishwa Vidyapeetham and Springer Nature, under which "+
        "article processing charges are waived for corresponding authors affiliated with Amrita Vishwa Vidyapeetham.")]),

      p([rb("Author Contributions  "),r("Adwitiya Mukhopadhyay: Conceptualization, Methodology, Supervision, "+
        "Patent application, Writing – review and editing. Saadhan P: Software, Protocol implementation, "+
        "Performance evaluation, Visualization (QFlux dashboard), Writing – original draft. "+
        "Rashmitha S: Protocol co-design (Aurora), Usability study design and execution, "+
        "Data curation, Statistical analysis, Writing – review and editing. "+
        "All authors read and approved the final manuscript.")]),

      p([rb("Acknowledgements  "),r("The authors thank the twelve graduate researchers who participated "+
        "in the usability study. The authors acknowledge the open-source developers of PyQtGraph, "+
        "FastAPI, websockets, and PyQt5. The authors thank anonymous reviewers for constructive feedback.")]),

      p([rb("AI-Assisted Writing Disclosure  "),r("AI-assisted writing tools were used during preparation of "+
        "this manuscript for language refinement, structural organization, and formatting. All scientific "+
        "content — protocol design, experimental methodology, data collection, analysis, and conclusions "+
        "— is entirely the original work of the authors. The authors take full responsibility for accuracy, "+
        "integrity, and originality. In accordance with Springer Nature's generative AI policy (2024), "+
        "no AI tool is listed as an author.")]),

      p([rb("Preliminary Work  "),r("Elements of the QFlux visualization system were presented in preliminary "+
        "form at the IEEE Signal Processing and Communications (SPCOM) conference (SPCOM 2024). "+
        "The present paper represents a substantially extended and revised work, integrating the Aurora "+
        "protocol as a primary contribution with full experimental evaluation that was not part of "+
        "the conference submission.")]),

      // ══════════════════════════════════════════════════════════════════
      // REFERENCES
      // ══════════════════════════════════════════════════════════════════
      sec("References"),

      ref("[1]  Bennett CH, Brassard G (1984) Quantum cryptography: public key distribution and coin tossing. In: Proc. IEEE Int. Conf. Computers, Systems and Signal Processing, Bangalore, India, pp 175–179"),
      ref("[2]  Ekert AK (1991) Quantum cryptography based on Bell's theorem. Phys Rev Lett 67(6):661–663. https://doi.org/10.1103/PhysRevLett.67.661"),
      ref("[3]  Shor PW (1994) Algorithms for quantum computation: discrete logarithms and factoring. In: Proc. 35th Annual Symp. Foundations of Computer Science, Santa Fe, NM, USA, pp 124–134"),
      ref("[4]  Scarani V, Bechmann-Pasquinucci H, Cerf NJ, Dusek M, Lutkenhaus N, Peev M (2009) The security of practical quantum key distribution. Rev Mod Phys 81(3):1301–1350. https://doi.org/10.1103/RevModPhys.81.1301"),
      ref("[5]  Gisin N, Ribordy G, Tittel W, Zbinden H (2002) Quantum cryptography. Rev Mod Phys 74(1):145–195. https://doi.org/10.1103/RevModPhys.74.145"),
      ref("[6]  Scarani V, Acín A, Ribordy G, Gisin N (2004) Quantum cryptography protocols robust against photon number splitting attacks for weak laser pulse implementations. Phys Rev Lett 92(5):057901. https://doi.org/10.1103/PhysRevLett.92.057901"),
      ref("[7]  Coopmans T et al (2021) NetSquid, a network simulator for quantum information using discrete events. Commun Phys 4:164. https://doi.org/10.1038/s42005-021-00647-8"),
      ref("[8]  Dahlberg A, Wehner S (2018) SimulaQron — a simulator for developing quantum internet software. Quantum Sci Technol 4(1):015001. https://doi.org/10.1088/2058-9565/aad56e"),
      ref("[9]  Grafana Labs (2023) Grafana: the open observability platform. https://grafana.com"),
      ref("[10] Elastic NV (2023) Kibana: your window into the Elastic Stack. https://www.elastic.co/kibana"),
      ref("[11] Stucki D et al (2009) High rate, long-distance quantum key distribution over 250 km of ultra low loss fibres. New J Phys 11:075003. https://doi.org/10.1088/1367-2630/11/7/075003"),
      ref("[12] Gobby C, Yuan ZL, Shields AJ (2004) Quantum key distribution over 122 km of standard telecom fiber. Appl Phys Lett 84(19):3762–3764. https://doi.org/10.1063/1.1738173"),
      ref("[13] Clauser JF, Horne MA, Shimony A, Holt RA (1969) Proposed experiment to test local hidden-variable theories. Phys Rev Lett 23(15):880–884. https://doi.org/10.1103/PhysRevLett.23.880"),
      ref("[14] Lo H-K, Curty M, Qi B (2012) Measurement-device-independent quantum key distribution. Phys Rev Lett 108(13):130503. https://doi.org/10.1103/PhysRevLett.108.130503"),
      ref("[15] Lucamarini M, Yuan ZL, Dynes JF, Shields AJ (2018) Overcoming the rate–distance limit of quantum key distribution without quantum repeaters. Nature 557:400–403. https://doi.org/10.1038/s41586-018-0066-6"),
      ref("[16] Pironio S et al (2009) Device-independent quantum key distribution secure against collective attacks. New J Phys 11:045021. https://doi.org/10.1088/1367-2630/11/4/045021"),
      ref("[17] Brassard G, Salvail L (1994) Secret-key reconciliation by public discussion. In: Advances in Cryptology — EUROCRYPT '93, Lecture Notes in Computer Science, vol 765. Springer, Berlin, pp 410–423"),
      ref("[18] Bangor A, Kortum P, Miller J (2009) Determining what individual SUS scores mean: adding an adjective rating scale. J Usability Stud 4(3):114–123"),
      ref("[19] Wehner S, Elkouss D, Hanson R (2018) Quantum internet: a vision for the road ahead. Science 362(6412):eaam9288. https://doi.org/10.1126/science.aam9288"),
      ref("[20] Dunjko V, Briegel HJ (2018) Machine learning and artificial intelligence in the quantum domain: a review of recent progress. Rep Prog Phys 81(7):074001. https://doi.org/10.1088/1361-6633/aab406"),
      ref("[21] Liao S-K et al (2017) Satellite-to-ground quantum key distribution. Nature 549:43–47. https://doi.org/10.1038/nature23655"),
      ref("[22] Yin J et al (2020) Entanglement-based secure quantum cryptography over 1,120 kilometres. Nature 582:501–505. https://doi.org/10.1038/s41586-020-2401-y"),
      ref("[23] Hunter JD (2007) Matplotlib: a 2D graphics environment. Comput Sci Eng 9(3):90–95. https://doi.org/10.1109/MCSE.2007.55"),
      ref("[24] Campagnola L (2023) PyQtGraph: scientific graphics and GUI library for Python. https://www.pyqtgraph.org"),
      ref("[25] Fette I, Melnikov A (2011) The WebSocket protocol. IETF RFC 6455. https://doi.org/10.17487/RFC6455"),
      ref("[26] Hart SG, Staveland LE (1988) Development of NASA-TLX (Task Load Index): results of empirical and theoretical research. In: Hancock PA, Meshkati N (eds) Human mental workload. North-Holland, Amsterdam, pp 139–183"),
      ref("[27] Brooke J (1996) SUS — a quick and dirty usability scale. In: Jordan PW et al (eds) Usability evaluation in industry. Taylor & Francis, London, pp 189–194"),
      ref("[28] Shneiderman B (1996) The eyes have it: a task by data type taxonomy for information visualizations. In: Proc. IEEE Symp. Visual Languages, pp 336–343. https://doi.org/10.1109/VL.1996.545307"),
      ref("[29] M R, Ramesha SS, Mukhopadhyay A (2025) QCAE-QOC-SVM: a hybrid quantum machine learning model for DoS and Fuzzy attack detection on autonomous vehicle CAN bus. MethodsX 15:103471"),
      ref("[30] Mukhopadhyay A, Rao A, Joshi P, Harish V (2024) Edge based blind spot avoidance and speed monitoring for emergency vehicles. Procedia Comput Sci 235:284–302"),
      ref("[31] J VS, Mukhopadhyay A (2025) A secured Internet of Drone model with distributed protocols. Procedia Comput Sci 252:665–673"),
      ref("[32] Ma X, Qi B, Zhao Y, Lo H-K (2005) Practical decoy state for quantum key distribution. Phys Rev A 72:012326. https://doi.org/10.1103/PhysRevA.72.012326"),

];

// Post-process to group bullets and references
let out = "";
let currentList = null;

for (let item of children) {
    if (!item) continue;
    if (Array.isArray(item)) {
        for (let sub of item) {
            out += sub;
        }
        continue;
    }
    let str = item.toString();
    
    // Check if it's a bullet
    if (str.startsWith('\\item') && !str.includes('\\bibitem')) {
        if (currentList !== 'itemize') {
            if (currentList) out += `\\end{${currentList}}\n\n`;
            out += `\\begin{itemize}\n`;
            currentList = 'itemize';
        }
        out += str;
    } else if (str.startsWith('\\bibitem')) {
        if (currentList !== 'thebibliography') {
            if (currentList) out += `\\end{${currentList}}\n\n`;
            out += `\\begin{thebibliography}{99}\n`;
            currentList = 'thebibliography';
        }
        out += str;
    } else {
        if (currentList) {
            out += `\\end{${currentList}}\n\n`;
            currentList = null;
        }
        out += str;
    }
}

if (currentList) {
    out += `\\end{${currentList}}\n\n`;
}

console.log(out);
