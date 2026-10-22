# Formula Audit: Biased-Basis BB84 (LCA) and Finite-Key Security Bounds

This audit documents every formula implemented for the Lo-Chau-Ardehali (LCA) biased-basis BB84 engine and the finite-key security analysis, directly referencing the source papers in `docs/papers/`.

---

## 1. Inventory of Source Papers (`docs/papers/`)

The following papers were verified in `docs/papers/`:

1. **Lo-Chau-Ardehali 2005 (LCA)**:
   - File: `docs/papers/0011056v3.pdf`
   - Title: *Efficient Quantum Key Distribution Scheme And Proof of Its Unconditional Security*
   - Authors: Hoi-Kwong Lo, H. F. Chau, M. Ardehali
   - Citation: arXiv:quant-ph/0011056v3 (8 Jul 2005) / *Journal of Cryptology* 18, 133–165 (2005).

2. **Tomamichel-Lim-Gisin-Renner 2012 (TLGR)**:
   - File: `docs/papers/1103.4130v2.pdf`
   - Title: *Tight Finite-Key Analysis for Quantum Cryptography*
   - Authors: Marco Tomamichel, Charles Ci Wen Lim, Nicolas Gisin, Renato Renner
   - Citation: arXiv:1103.4130v2 (13 Dec 2011) / *Nature Communications* 3, Article 634 (2012).

3. **Lim et al. 2014**:
   - File: `docs/papers/1311.7129v1.pdf`
   - Title: *Concise Security Bounds for Practical Decoy-State Quantum Key Distribution*
   - Authors: Charles Ci Wen Lim, Marcos Curty, Nino Walenta, Feihu Xu, Hugo Zbinden
   - Citation: arXiv:1311.7129v1 (27 Nov 2013) / *Phys. Rev. A* 89, 022307 (2014).

4. **Additional Reference in `docs/papers/`**:
   - File: `docs/papers/1506.08458v3.pdf`
   - Title: *A largely self-contained and complete security proof for quantum key distribution*
   - Authors: Marco Tomamichel, Anthony Leverrier
   - Citation: arXiv:1506.08458v3 (11 Jul 2017) / *Quantum* 1, 14 (2017).

---

## 2. Answers to TASK 0c

### (i) Does the Tomamichel et al. (2012) analysis cover biased basis choice?
**Yes.**
In Section *Protocol Definition* and Table I (pages 4–5):
> *"We now define a family of protocols, $\Phi[n, k, \ell, Q_{\text{tol}}, \epsilon_{\text{cor}}, \text{leak}_{\text{EC}}]$... The protocol is asymmetric, so that the number of bits measured in the two bases ($n$ bits in the $X$ basis and $k$ bits in the $Z$ basis) are not necessarily equal [41]."*
> *"Alice chooses a basis $a_i \in \{X, Z\}$, where $X$ is chosen with probability $p_x = (1 + \sqrt{k/n})^{-1}$ and $Z$ with probability $p_z = 1 - p_x$."*

In the paper's conclusion (page 7):
> *"In conclusion, this article gives tight finite-key bounds for secure quantum key distribution with an asymmetric BB84 protocol."*

### (ii) Which attack class does it cover?
**General Attacks (Coherent Attacks).**
In *Security Analysis* and *Discussion* (pages 5 & 7):
> *"Distribution: Alice sends the qubit over the quantum channel to Bob. (Recall that Eve is allowed to arbitrarily interact with the system and we do not make any assumptions about what Bob receives.)"* (Table I, page 5)
> *"Most previous security proofs against general adversaries, e.g. [7, 18, 20, 21], are arranged in two steps: An analysis of the security against adversaries restricted to collective attacks and a lifting of this argument to general attacks... In our proof we consider general attacks directly."* (Page 7)

### (iii) Which parameters ($n, k, Q_{\text{tol}}, \text{leak}_{\text{EC}}, \epsilon_{\text{cor}}, \epsilon_{\text{sec}}$) must be fixed before the run, and what does the protocol do if the observed test error exceeds the tolerance?
- **Parameters fixed before run**:
  All parameters defining the protocol family $\Phi[n, k, \ell, Q_{\text{tol}}, \epsilon_{\text{cor}}, \text{leak}_{\text{EC}}]$ and security target $\epsilon_{\text{sec}}$ are predetermined and fixed *prior* to executing the quantum transmission and parameter estimation. Specifically:
  - $n$: raw key block size.
  - $k$: parameter estimation sample size in the conjugate/test basis.
  - $Q_{\text{tol}}$: channel error tolerance threshold.
  - $\text{leak}_{\text{EC}}$: budgeted maximum error correction leakage.
  - $\epsilon_{\text{cor}}$: correctness error budget (hash collision probability bound).
  - $\epsilon_{\text{sec}}$: secrecy failure probability budget.
- **Protocol Action on Exceeding Tolerance**:
  Under *Parameter Estimation* (Table I, page 5):
  > *"Next, they compute the average error $\lambda := \frac{1}{|Z|} \sum y_i \oplus y'_i$, where the sum is over all $i \in Z$. The protocol aborts if $\lambda > Q_{\text{tol}}$."*
  If the observed test error exceeds $Q_{\text{tol}}$, the protocol immediately **aborts** and outputs zero secret key bits ($\ell = 0$).

---

## 3. Detailed Formula Audit

### Formula 1: Detection & Sifting Model (Physical Channel Model)
- **Source Paper**: Built upon standard prepare-and-measure detection model shared with honest BB84 (`backend/protocols/bb84.py`), verified against LCA 2005 Protocol E (Section 4.3).
- **Printed Expressions**:
  - Photon detection probability: $p_{\text{detect}} = \eta_{\text{ch}} \cdot \eta_{\text{det}}$, where $\eta_{\text{ch}} = 10^{-\alpha L / 10}$.
  - Dark count probability per gate: $p_{\text{dark}} = d_c \cdot \Delta t$.
  - Detection event: $\text{click} = \text{photon\_detected} \lor \text{dark\_count}$.
  - Independent basis choice: Alice chooses $Z$ with probability $p_Z$ and $X$ with $1 - p_Z$; Bob chooses $Z$ with probability $p_Z$ and $X$ with $1 - p_Z$ independently.
  - Classification into 4 disjoint sets:
    $$ZZ = \{i \mid a_i = Z, b_i = Z, \text{click}_i\}, \quad XX = \{i \mid a_i = X, b_i = X, \text{click}_i\}$$
    $$ZX = \{i \mid a_i = Z, b_i = X, \text{click}_i\}, \quad XZ = \{i \mid a_i = X, b_i = Z, \text{click}_i\}$$
  - Sifting: Keep $ZZ$ and $XX$; discard mismatched $ZX$ and $XZ$.
  - Sifting efficiency:
    $$\text{sifting\_efficiency} = \frac{n_{ZZ} + n_{XX}}{n_{\text{detected}}}$$
    Asymptotically, $\mathbb{E}[n_{ZZ} + n_{XX}] / n_{\text{detected}} = p_Z^2 + (1 - p_Z)^2$. For $p_Z = 0.5$, this reduces exactly to $0.5^2 + 0.5^2 = 0.5$.
- **Symbol Definitions**:
  - $a_i, b_i \in \{Z, X\}$: Alice's and Bob's basis choices.
  - $\eta_{\text{ch}}$: fiber transmission efficiency.
  - $\eta_{\text{det}}$: detector efficiency.
  - $d_c$: dark count rate (Hz); $\Delta t$: time gate width (s).
  - $e_{\text{channel}}$: physical channel outcome-flip probability (polarization misalignment).
- **Assumptions & Conditions**:
  - Single-photon / single-mode qubit approximation.
  - Detection probability independent of basis choices (no detector-efficiency loophole, as required by TLGR 2012, page 4).

---

### Formula 2: Basis-Specific Error Estimation (Lo-Chau-Ardehali 2005)
- **Source Paper**: Lo-Chau-Ardehali (2005), Section 4.2 (*Refined Error Analysis*), Section 4.3 (*Protocol E*), Steps (6)–(8), and Section 4.4 (Eq. 27–29).
- **Printed Expressions**:
  - Step (7), page 28:
    > *"From the subset where they both use the rectilinear basis, Alice and Bob randomly pick a fixed number say $m_1$ photons and publicly compare their polarizations... The number of mismatches $r_1$ tells them the estimated error rate $e_1 = r_1 / m_1$. Similarly, from the subset where they both use the diagonal basis, Alice and Bob randomly pick a fixed number say $m_2$ photons and publicly compare their polarizations. The number of mismatches $r_2$ gives the estimated error rate $e_2 = r_2 / m_2$."*
  - Section 4.4, page 29:
    > *"If the key is generated only from polarization data in say the Z-basis, then clearly, the bit-flip error rate is simply the Z-basis bit error rate and the phase error rate is simply the X-basis bit error rate."*
  - Therefore:
    - Bit error rate estimate: $e_{Z,\text{est}} = \frac{r_Z}{k_Z}$ from a sample of $k_Z$ bits from $ZZ$.
    - Raw key length: $n = n_{ZZ} - k_Z$ bits from the remaining untested $ZZ$ events.
    - Phase error rate estimate: $e_{X,\text{est}} = \frac{r_X}{k_X}$ from $k_X$ bits of $XX$ (where $k_X \le n_{XX}$, typically all $n_{XX}$ test events).
- **Symbol Definitions**:
  - $k_Z$ ($m_1$): number of $ZZ$ events sampled and sacrificed for bit error estimation.
  - $r_Z$: observed bit errors in the $k_Z$ sample.
  - $k_X$ ($m_2$): number of $XX$ events compared for phase error estimation.
  - $r_X$: observed bit errors in the $k_X$ sample.
- **Assumptions & Conditions**:
  - Raw key is extracted strictly from the dominant basis ($ZZ$).
  - Conjugate basis events ($XX$) are used strictly for phase-error estimation and completely discarded.

---

### Formula 3: Asymptotic LCA Key Rate
- **Source Paper**: Lo-Chau-Ardehali (2005), Section 3.6 (page 21) & Section 4.4 (Eq. 27).
- **Printed Expression**:
  In CSS-based key distillation:
  $$r_{\text{asym}} = \max\left(0,\, 1 - f_{\text{EC}} h_2(e_Z) - h_2(e_X)\right)$$
  where $h_2(p) = -p \log_2 p - (1-p) \log_2(1-p)$ is the binary entropy function, and $f_{\text{EC}} \ge 1.0$ is the information reconciliation efficiency factor (Shannon limit $f_{\text{EC}} = 1.0$; realistic Cascade/LDPC $f_{\text{EC}} \approx 1.16$).
  In terms of secret key bits per sent pulse:
  $$R_{\text{asym, sent}} = \frac{n_{ZZ} - k_Z}{N} \cdot \max\left(0,\, 1 - f_{\text{EC}} h_2(e_Z) - h_2(e_X)\right)$$
- **Symbol Definitions**:
  - $e_Z$: bit error rate in key basis ($Z$).
  - $e_X$: phase error rate in test basis ($X$).
  - $N$: total pulses transmitted.

---

### Formula 4: Finite-Key Security Bound (Tomamichel-Lim-Gisin-Renner 2012)
- **Source Paper**: Tomamichel, Lim, Gisin, Renner (2012), Section *Security Analysis*, Eq. (2) (page 5) and Supplementary Material Eq. (S3)–(S4) (page 12).
- **Printed Expressions**:
  - Main text Eq. (2):
    $$\ell \le n \left( q - h(Q_{\text{tol}} + \mu) \right) - \text{leak}_{\text{EC}} - \log_2 \frac{2}{\epsilon_{\text{sec}}^2 \epsilon_{\text{cor}}}$$
    where:
    $$\mu := \sqrt{\frac{n+k}{nk} \frac{k+1}{k} \ln \frac{4}{\epsilon_{\text{sec}}}}$$
  - Preparation quality: $q = 1$ for BB84 qubit states (page 4).
  - Truncated binary entropy (Footnote 1, page 12):
    $$h(x) = \begin{cases} -x \log_2 x - (1-x) \log_2(1-x), & x \le 0.5 \\ 1.0, & x > 0.5 \end{cases}$$
  - Statistical deviation $\mu$: Derived from Serfling-type bound for sampling without replacement (Supplementary Note 1, Eq. S10–S13).
  - Error correction leakage model:
    $$\text{leak}_{\text{EC}} = f_{\text{EC}} \cdot n \cdot h_2(e_{Z,\text{est}})$$
    (In the paper discussion, page 7, $\text{leak}_{\text{EC}} = \xi n h(Q_{\text{tol}})$; when estimating from the empirical sample, $\text{leak}_{\text{EC}} = f_{\text{EC}} n h_2(e_{Z,\text{est}})$).
  - Integer secret key length:
    $$\ell = \max\left(0,\, \left\lfloor n (q - h(Q_{\text{tol}} + \mu)) - \text{leak}_{\text{EC}} - \log_2 \frac{2}{\epsilon_{\text{sec}}^2 \epsilon_{\text{cor}}} \right\rfloor\right)$$
  - Supplementary Note 1, Eq. (S3)–(S4) (General 2-parameter formulation):
    $$\ell \le \max_{\epsilon, \bar{\epsilon}} \left\lfloor n (q - h(Q_{\text{tol}} + \mu(\epsilon))) - 2 \log_2 \frac{1}{2\bar{\epsilon}} - \text{leak}_{\text{EC}} - \log_2 \frac{2}{\epsilon_{\text{cor}}} \right\rfloor$$
    with $2\epsilon + \bar{\epsilon} \le \epsilon_{\text{sec}}$ and $\mu(\epsilon) = \sqrt{\frac{n+k}{nk} \frac{k+1}{k} \ln \frac{1}{\epsilon}}$.
    Note that Eq. (2) corresponds directly to the fixed analytical choice $\epsilon = \epsilon_{\text{sec}} / 4, \bar{\epsilon} = \epsilon_{\text{sec}} / 2$.
- **Abort Condition**:
  If the observed test error in the phase-estimation basis $e_{X,\text{est}} > Q_{\text{tol}}$, protocol aborts: $\ell = 0, \text{aborted} = \text{True}$.
- **Symbol Definitions**:
  - $n$: number of key bits.
  - $k$: number of parameter estimation test bits.
  - $Q_{\text{tol}}$: error tolerance threshold.
  - $\mu$: statistical fluctuation parameter.
  - $\epsilon_{\text{sec}}$: secrecy failure probability.
  - $\epsilon_{\text{cor}}$: correctness error probability.

---

### Formula 5: Decoy-State Finite-Key Bound (Lim et al. 2014) — Scope Analysis
- **Source Paper**: Lim, Curty, Walenta, Xu, Zbinden (2014), Eq. (1)–(5) (pages 2–3).
- **Printed Expression**:
  $$\ell = \left\lfloor s_{X,0} + s_{X,1} - s_{X,1} h(\phi_X) - \text{leak}_{\text{EC}} - 6 \log_2 \frac{21}{\epsilon_{\text{sec}}} - \log_2 \frac{2}{\epsilon_{\text{cor}}} \right\rfloor \quad \text{(Eq. 1)}$$
  where $s_{X,0}$ is the estimated vacuum count, $s_{X,1}$ is the estimated single-photon count, $\phi_X$ is the upper bound on the single-photon phase error rate:
  $$\phi_X := \frac{c_{X,1}}{s_{X,1}} \le \frac{v_{Z,1}}{s_{Z,1}} + \gamma\left(\epsilon_{\text{sec}}, \frac{v_{Z,1}}{s_{Z,1}}, s_{Z,1}, s_{X,1}\right) \quad \text{(Eq. 5)}$$
- **Applicability Assessment**:
  - Lim et al. 2014 is derived specifically for *decoy-state* protocols using weak coherent pulses with multiple intensity levels ($\mu_1, \mu_2, \mu_3$).
  - The security parameter term $-6 \log_2(21 / \epsilon_{\text{sec}})$ accounts for a union bound over 6 individual concentration inequalities (vacuum and single-photon bounds across multiple intensities).
  - For single-photon qubit prepare-and-measure protocols (as modeled here), $s_{X,0} = 0$ and all detected key events are single-photon events ($s_{X,1} = n$). In this non-decoy qubit setting, TLGR 2012 is the exact, tight, and directly applicable bound. Lim et al.'s formula is documented and contrasted accordingly.

---

## 4. Tensions and Notational Conventions

1. **Basis labeling**:
   - In LCA 2005: "rectilinear" is assigned probability $p$ and "diagonal" probability $1-p$. Key is distilled from the dominant basis (diagonal).
   - In TLGR 2012: $X$ is used for raw key generation ($n$ bits) with probability $p_x = (1 + \sqrt{k/n})^{-1}$, and $Z$ is used for parameter estimation ($k$ bits) with probability $p_z$.
   - In our engine convention (specified in TASK 1): $Z$ is the key generation basis (selected with probability $p_Z$), and $X$ is the phase-error parameter estimation basis (selected with probability $1 - p_Z$). The mathematics is completely symmetric under basis relabeling.

2. **Error Correction Leakage**:
   - In theoretical papers, $\text{leak}_{\text{EC}}$ is often budgeted in advance as $\xi n h_2(Q_{\text{tol}})$.
   - In physical simulation with honest parameter estimation, $\text{leak}_{\text{EC}} = f_{\text{EC}} \cdot n \cdot h_2(e_{Z,\text{est}})$. Both models are documented and supported.
