# Practical Guide to Fitting Dielectric Spectra (Extended)

**DS, HN, Debye–Lorentz, Debye, Cole–Cole, Cole–Davidson, Multi-Debye + Kramers–Kronig checks**

*This extended guide builds on the unified document you approved and adds Debye, Cole–Cole, Cole–Davidson, multi-Debye models, plus a practical Kramers–Kronig (KK) causality workflow.*

---

## 0) Quick Model Picker (Read First)

1. **Nearly constant tan δ**; ε'(ω) falls slowly with log f; no distinct peaks → **Djordjević–Sarkar (DS)**
2. **Single narrow, symmetric loss peak** → **Debye**. **Two+ distinct symmetric peaks** → **Multi-Debye**
3. **Broad, symmetric peak** (depressed semicircle in Cole–Cole plot) → **Cole–Cole**. **Broad, asymmetric peak** (long HF tail) → **Cole–Davidson** or **HN**
4. **Broad, skewed peak with tunable shape** (needs both width & asymmetry) → **Havriliak–Negami (HN)**
5. **Relaxations + sharp resonances** together → **Debye–Lorentz**
6. **Low-frequency 1/ω rise in ε''**? Include **conductivity** term (all models)

---

## 1) Differences at a Glance

| Model | When to use | Core idea | Typical parameters | Practical notes |
|-------|-------------|-----------|-------------------|-----------------|
| **DS** | Smooth broadband spectra; nearly constant tan δ | Log "wideband Debye" between ω₁, ω₂ | ε∞, Δε, ω₁, ω₂, σdc | Causal; easy to seed from one Dk/tan δ; set ω₁, ω₂ **outside** band |
| **Debye** | Narrow, symmetric single relaxation | Single time constant | ε∞, Δε, τ, σdc | ε'' peak at ωτ=1; great baseline for more complex models |
| **Cole–Cole** | Broad **symmetric** peak | Debye with symmetric broadening | ε∞, Δε, τ, α, σdc | 0<α<1; depressed semicircle in Cole–Cole plot |
| **Cole–Davidson** | Broad **asymmetric** peak (long HF tail) | Debye with HF-tail skew | ε∞, Δε, τ, β, σdc | 0<β<1; skewed arc in Cole–Cole plot |
| **HN** | Broad & asymmetric peak (max flexibility) | Debye with width (α) & skew (β) | εs, ε∞, τ, α, β, σdc, s≈1 | Encompasses Debye/CC/CD as special cases; robust for polymers |
| **Multi-Debye** | Multiple **distinct** symmetric relaxations | Sum of Debyes | ε∞, {Δεₖ, τₖ} | Keep N minimal; watch parameter correlation; consider AIC/BIC |
| **Debye–Lorentz** | Relaxations + **resonances** | Debye + Lorentz oscillators | ε∞, ADk, τₖ, ALm, ω0m, δm | Add -iσdc/(ε₀ω) if LF tail exists |

---

## 2) Shared Workflow (Applies to All Models)

### 2.1 Preprocess Once, Fit Many

- **Gentle smoothing** (e.g., Savitzky–Golay). Apply identically to ε' and ε''
- **Baseline / drift**: fix LF drift before fitting
- **High-frequency "hook" correction** (parasitic Cp):

$$Z_{\text{true}}(\omega) = \frac{Z_{\text{meas}}(\omega)}{1 - i\omega C_p Z_{\text{meas}}(\omega)}$$

Then convert Z_true → ε*. Estimate Cp from HF susceptance slope.

### 2.2 Fitting Engine & Metrics

- **Solver:** Nonlinear least squares (Levenberg–Marquardt). Fit ε' and ε'' together
- **Primary metrics:** **RMSE** and **reduced χ²** (if weighted). **Avoid R²** for nonlinear fits
- **Residuals:** must look like structure-free noise vs. frequency
- **Correlation matrix:** |r|>0.95 ⇒ identifiability problems; use bounds or simplify

---

## 3) Model Playbooks

### 3.1 Djordjević–Sarkar (DS)

**Equation (with conduction):**

$$\varepsilon^*(\omega) = \varepsilon_\infty + \frac{\Delta\varepsilon}{\ln(\omega_2/\omega_1)} \ln\left(\frac{\omega_2 + i\omega}{\omega_1 + i\omega}\right) - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

Use when tan δ is flat across decades and ε' declines slowly with log f. Causal / KK-consistent. Seed from one Dk/tan δ point if needed.

### 3.2 Havriliak–Negami (HN)

**Equation (with conduction):**

$$\varepsilon^*(\omega) = \varepsilon_\infty + \frac{\varepsilon_s - \varepsilon_\infty}{[1 + (i\omega\tau)^\alpha]^\beta} - \frac{i\sigma_{dc}}{\varepsilon_0 \omega^s}$$

where 0 < α ≤ 1, 0 < β ≤ 1, s ≈ 1

**Peak frequency** (helps seed τ):

$$\omega_{max} = \tau^{-1} \left[\frac{\sin\left(\frac{\pi\alpha}{2(1+\beta)}\right)}{\sin\left(\frac{\pi\alpha\beta}{2(1+\beta)}\right)}\right]^{1/\alpha}$$

HN covers Debye, Cole–Cole, Cole–Davidson as special cases.

### 3.3 Debye–Lorentz (D–L)

**Equation (hybrid, add conduction if needed):**

$$\varepsilon(\omega) = \varepsilon_\infty + \sum_{k=1}^{N_D} \frac{A_{Dk}}{1 + i\omega\tau_k} + \sum_{m=1}^{N_L} \frac{A_{Lm}\omega_{0m}^2}{\omega_{0m}^2 - \omega^2 - 2i\delta_m\omega} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

Use for **relaxations + resonances**. Seed τₖ from loss-peak fmax, ω0m from resonances, and δm from width via Q ≈ ω₀/(2δ).

### 3.4 Debye (Single-Pole)

**Equation (optionally with conduction):**

$$\varepsilon^*(\omega) = \varepsilon_\infty + \frac{\Delta\varepsilon}{1 + i\omega\tau} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

**Use when** the loss peak is **narrow and symmetric**; Cole–Cole plot is a perfect semicircle.

**Inits:** τ ≈ (2πfmax)⁻¹; Δε ≈ 2ε''max; ε∞ from HF ε'.

### 3.5 Cole–Cole (CC)

**Equation (symmetric broadening):**

$$\varepsilon^*(\omega) = \varepsilon_\infty + \frac{\Delta\varepsilon}{1 + (i\omega\tau)^\alpha} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

where 0 < α < 1

**Use when** the peak is **broadened but symmetric** (depressed semicircle).

**Inits:** start α ∈ [0.7, 0.95]; τ from fmax (Debye estimate) then refine; Δε, ε∞ as in Debye.

### 3.6 Cole–Davidson (CD)

**Equation (asymmetric HF tail):**

$$\varepsilon^*(\omega) = \varepsilon_\infty + \frac{\Delta\varepsilon}{(1 + i\omega\tau)^\beta} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

where 0 < β < 1

**Use when** the loss peak has a **long high-frequency tail** (skewed arc).

**Inits:** β ∈ [0.5, 0.9]; τ from fmax; other params as in Debye.

### 3.7 Multi-Debye (N-pole Debye)

**Equation:**

$$\varepsilon^*(\omega) = \varepsilon_\infty + \sum_{k=1}^N \frac{\Delta\varepsilon_k}{1 + i\omega\tau_k} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

**Use when** you see **multiple distinct symmetric** relaxations.

**Inits:** one Debye per visible peak (τₖ ≈ (2πfmax,k)⁻¹; Δεₖ ≈ 2ε''max,k). Keep N minimal; monitor parameter correlation (|r|>0.95). Consider AIC/BIC if adding/removing poles.

---

## 4) Kramers–Kronig (KK) Causality Analysis (Practical)

**Why:** Causal materials must satisfy KK relations that tie ε' and ε''. Use KK to **validate data**, **separate conduction**, and **cross-check fits**. DS/HN/CC/CD/Debye/D–L forms are causal; measured data and preprocessing must also be consistent.

### 4.1 Standard KK Relations (Loss ↔ Dispersion)

Assuming ε∞ known and σdc handled separately:

$$\varepsilon'(\omega) - \varepsilon_\infty = \frac{2}{\pi} \mathcal{P}\int_0^\infty \frac{\Omega\varepsilon''(\Omega)}{\Omega^2 - \omega^2} d\Omega$$

$$\varepsilon''(\omega) = -\frac{2\omega}{\pi} \mathcal{P}\int_0^\infty \frac{\varepsilon'(\Omega) - \varepsilon_\infty}{\Omega^2 - \omega^2} d\Omega$$

### 4.2 Subtractive KK (Better for Finite Bands)

Choose an **anchor** ω₀ (usually near the band center):

$$\varepsilon'(\omega) - \varepsilon'(\omega_0) = \frac{2(\omega^2 - \omega_0^2)}{\pi} \mathcal{P}\int_0^\infty \frac{\Omega\varepsilon''(\Omega)}{(\Omega^2 - \omega^2)(\Omega^2 - \omega_0^2)} d\Omega$$

and the reciprocal formula for ε''. This reduces truncation error.

### 4.3 Hands-on KK Workflow

1. **Preprocess** (smoothing, hook correction, baseline) and **remove conduction**:  
   ε''dip(ω) = ε''(ω) - σdc/(ε₀ω)

2. **Set tails/extrapolation:**  
   - LF: ε'' ~ σdc/(ε₀ω) (removed above)
   - HF: ε' → ε∞
   - If needed, extend with your chosen model (e.g., Debye/HN) to stabilize the integrals

3. **Integrate on a log grid** (trapezoid/Simpson) using **SSKK** with anchor at mid-band

4. **KK residuals:**  
   - δ''(ω) = ε''meas - KK[ε']
   - δ'(ω) = ε'meas - KK[ε'']
   - They should look like **noise**; quote **RMSE** of KK residuals

5. **Model cross-check:** Run KK on the **fitted model** too; the model should be self-consistent and match KK-reconstructed curves within noise

**Tip:** If KK residuals show a **broad feature**, your model likely misses a relaxation; if they show **HF curl**, re-check hook correction.

---

## 5) Fit Evaluation & Reporting (Checklist)

1. **Preprocessing summary** (smoothing, baseline, hook correction with Cp)
2. **Final parameters** with **±** errors and **bounds** used; list σdc explicitly
3. **Goodness-of-fit:** **RMSE** (+ reduced χ² if weighted). **Do not use R²**
4. **Residual plots** for ε' and ε'' vs. f (no structure)
5. **Parameter correlation matrix** (flag |r|>0.95)
6. **KK validation**: include KK residual RMSE and a one-line verdict ("passes within noise" / "fails at HF due to hook", etc.)

---

## 6) Troubleshooting

- **HF curl ("hook") remains:** refine Cp from HF susceptance; re-apply correction
- **Residual shows broad leftover bump:** add one Debye/HN term; DS too rigid for that dataset
- **Unstable parameters / huge errors:** parameters highly correlated; bound or reduce model order; widen frequency span
- **LF 1/ω tail dominates:** include σdc explicitly before fitting relaxation terms
- **KK residual trends:** revisit extrapolations and anchor choice; try SSKK; verify ε∞ and σdc

---

## 7) Tear-off Formulas (Quick Reference)

**Debye (+ conduction)**
$$\varepsilon^* = \varepsilon_\infty + \frac{\Delta\varepsilon}{1 + i\omega\tau} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

**Cole–Cole (+ conduction)**
$$\varepsilon^* = \varepsilon_\infty + \frac{\Delta\varepsilon}{1 + (i\omega\tau)^\alpha} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

**Cole–Davidson (+ conduction)**
$$\varepsilon^* = \varepsilon_\infty + \frac{\Delta\varepsilon}{(1 + i\omega\tau)^\beta} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

**HN (+ conduction)**
$$\varepsilon^* = \varepsilon_\infty + \frac{\varepsilon_s - \varepsilon_\infty}{[1 + (i\omega\tau)^\alpha]^\beta} - \frac{i\sigma_{dc}}{\varepsilon_0\omega^s}$$

**Multi-Debye (+ conduction)**
$$\varepsilon^* = \varepsilon_\infty + \sum_k \frac{\Delta\varepsilon_k}{1 + i\omega\tau_k} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

**DS**
$$\varepsilon^* = \varepsilon_\infty + \frac{\Delta\varepsilon}{\ln(\omega_2/\omega_1)} \ln\frac{\omega_2 + i\omega}{\omega_1 + i\omega} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

**Debye–Lorentz (+ conduction)**
$$\varepsilon = \varepsilon_\infty + \sum \frac{A_D}{1 + i\omega\tau} + \sum \frac{A_L\omega_0^2}{\omega_0^2 - \omega^2 - 2i\delta\omega} - \frac{i\sigma_{dc}}{\varepsilon_0\omega}$$

with Q ≈ ω₀/(2δ)

**KK (standard)**
$$\varepsilon'(\omega) - \varepsilon_\infty = \frac{2}{\pi}\mathcal{P}\int_0^\infty \frac{\Omega\varepsilon''(\Omega)}{\Omega^2 - \omega^2} d\Omega$$

$$\varepsilon''(\omega) = -\frac{2\omega}{\pi}\mathcal{P}\int_0^\infty \frac{\varepsilon'(\Omega) - \varepsilon_\infty}{\Omega^2 - \omega^2} d\Omega$$