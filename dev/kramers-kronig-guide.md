# A Practical Guide to Using Kramers–Kronig (KK) Relations in Data Analysis — v2

This guide expands your original report with concrete, field‑tested practices for using Kramers–Kronig (KK) relations across **pre‑processing**, **fitting**, and **post‑fit validation**. It adds prerequisites, finite‑bandwidth cures (SSKK/MSKK, VKK), robust extrapolation, passivity checks, numerical tips, uncertainty propagation, a **KK residual checklist**, two end‑to‑end **workflows**, and ready‑to‑use **MATLAB snippets**.

> **What KK gives you.** KK links the real and imaginary parts of a complex response of a **linear, time‑invariant, causal** system. Use it as a physics constraint: it improves initial guesses, constrains models, diagnoses data problems, and validates results.

---

## 0) Scope & Prerequisites

KK applies when all of the following hold:

- **Linearity** and **time‑invariance (LTI)**.
- **Causality**: the impulse response is zero for \(t<0\).
- **Analyticity** of the response function in the upper half of the complex frequency plane.
- **Sufficient high‑frequency decay** (possibly after subtracting a constant \(f(\infty)\)).

### Conventions (state these in every report)
- **Fourier sign convention**: explicitly declare \(e^{-i\omega t}\) or \(e^{+i\omega t}\). Signs in KK flip with convention.
- **Quantity transformed**: susceptibility \(\chi\), permittivity \(\varepsilon\), conductivity \(\sigma\), impedance \(Z\), admittance \(Y\), or modulus \(M=1/\varepsilon\). Parity and asymptotics differ across these.
- **Passivity / positive‑realness**: for passive media under the \(e^{-i\omega t}\) convention, loss terms obey sign constraints (e.g., \(\mathrm{Im}\,\chi(\omega)\ge 0\) for \(\omega>0\)). For networks, \(Z(s)\) should be **positive‑real**: \(\mathrm{Re}\,Z(i\omega)\ge 0\).
- **Minimum‑phase caveat**: amplitude↔phase relations (Bode) are unique only for **minimum‑phase** systems. Zeros in the upper half‑plane add extra phase (Blaschke factors) not captured by the simple Hilbert relation.

### One‑sided KK (illustrative forms)
For a response \(f(\omega)\) with \(f(\infty)\) finite and using the \(e^{-i\omega t}\) convention,
\[
\mathrm{Re}\,f(\omega)=f(\infty)+\frac{2}{\pi}\,\mathcal{P}\!\!\int_0^\infty 
\frac{\omega' \,\mathrm{Im}\,f(\omega')}{\omega'^2-\omega^2}\,d\omega',
\quad
\mathrm{Im}\,f(\omega)=-\frac{2\omega}{\pi}\,\mathcal{P}\!\!\int_0^\infty 
\frac{\mathrm{Re}\,f(\omega')-f(\infty)}{\omega'^2-\omega^2}\,d\omega' .
\]

---

## 1) The Basics: Raw Data or a Model?

**Both.** KK operates on raw data, but practical KK requires extrapolation to \(0\) and \(\infty\), which introduces model assumptions.

### Two approaches
1. **Direct calculation (model‑assisted)**: integrate experimental data plus physically justified extrapolations. Accuracy depends on tail validity.
2. **Model fitting (model‑based)**: fit to a KK‑compliant model (e.g., Debye/Lorentz/Cole‑Cole, passive equivalent circuits). Use KK as a **constraint** and a **validation** framework.

> **Takeaway:** the principle is model‑free, but the practice is almost always **model‑assisted**.

---

## 2) Extrapolation That Respects Physics

Provide explicit, justified tails instead of arbitrary power laws:

- **Metals (optics)**  
  **Low‑\(\omega\):** Hagen–Rubens for reflectance \(R(\omega)\approx 1 - A\sqrt{\omega}\).  
  **Mid‑\(\omega\):** Drude (optionally Drude–Lorentz) anchored to measured DC \(\sigma_0\).  
  **High‑\(\omega\):** smoothly approach \(\varepsilon(\infty)\). If available, anchor to literature/x‑ray scattering factors.

- **Insulators / semiconductors (optics)**  
  **Low‑\(\omega\):** \(\varepsilon''\to 0\) smoothly as \(\omega\to 0\); enforce the correct static limit \(\varepsilon(0)\) if known.  
  **High‑\(\omega\):** approach \(\varepsilon(\infty)\) using literature or ab‑initio values.

- **Impedance spectroscopy (EIS)**  
  **Low‑\(\omega\):** enforce finite \(Z(0)\) (or known Warburg/CPE slope) and check for drift/polarization artifacts.  
  **High‑\(\omega\):** include lead inductance \(L\) and parasitics so that \(\mathrm{Im}\,Z\sim \omega L\).

### Sum‑rules as tail sanity checks
Use integrated spectral weight (e.g., optical \(f\)-sum rule for \(\sigma_1(\omega)\)) or energy conservation to detect missing bandwidth/stitching errors.

---

## 3) Finite‑Bandwidth Cures (Use These First)

- **Singly/Multiply‑Subtractive KK (SSKK/MSKK)**  
  Subtract one (or more) anchor points \((\omega_a, f(\omega_a))\) to accelerate convergence and suppress edge sensitivity.  
  Example SSKK for the real part:
  \[
  \mathrm{Re}\,f(\omega)-\mathrm{Re}\,f(\omega_a)=
  \frac{2(\omega^2-\omega_a^2)}{\pi}\,\mathcal{P}\!\!\int_0^\infty
  \frac{\omega'\,\mathrm{Im}\,f(\omega')}{(\omega'^2-\omega^2)(\omega'^2-\omega_a^2)}\,d\omega'.
  \]

- **Variational KK‑constrained analysis (VKK)**  
  Fit a flexible basis (splines / Drude–Lorentz oscillators) with KK enforced exactly. Lets the data decide line shapes while staying physical; excellent when you want “model‑free but KK‑consistent”.

- **EIS‑specific finite‑band tools**  
  **Z‑HIT (logarithmic Hilbert transform)**, **Lin‑KK**, and related methods provide robust KK checks over limited bands and are effective at detecting drift, inductive leads, or contact artifacts. Consider testing in \(Z^*\), \(Y^*\), and \(M^*\) representations; different forms separate processes differently.

---

## 4) Pre‑Processing: Set Up the Problem for Success

- **Parity‑aware mirroring**  
  Use one‑sided KK forms when possible. If you must mirror data, apply the correct even/odd symmetry implied by the specific response.

- **Frequency grids**  
  Prefer **log‑spaced** grids across decades. Precompute a **discrete Hilbert/KK kernel matrix** for your grid so KK becomes a fast matrix–vector multiply inside optimizers.

- **Principal value handling**  
  Remove the self‑term analytically (set diagonal kernel terms to zero and apply a small PV correction or local interpolation). Avoid naive inclusion of the singular point.

- **Windowing & padding**  
  Light windowing near band edges and moderate zero‑padding reduce ringing when using FFT‑Hilbert implementations.

- **Robust weighting and outliers**  
  Use robust loss (Huber/Tukey) and weight points by measurement uncertainty; KK smooths noise but will reflect systematic errors.

---

## 5) Using KK *Before* Fitting

- **Seed parameters with KK‑consistent targets**  
  Instead of fitting directly to noisy raw parts, first produce a KK‑consistent counterpart (via SSKK/VKK), then fit your model to this smoother target to get high‑quality initial parameters.

- **Bounds from physics**  
  Enforce passivity/positive‑realness as **hard bounds** (e.g., \(\mathrm{Im}\,\chi(\omega)\ge 0\); \(\mathrm{Re}\,Z(i\omega)\ge 0\)). Reject parameter sets that violate them without evaluating the objective.

- **Early model screening**  
  Discard models that cannot reproduce a KK‑consistent envelope resembling your data.

---

## 6) KK‑Consistent Model Families

- **Dielectrics/optics**: Debye, multi‑pole Debye, Cole–Cole, Cole–Davidson, Havriliak–Negami, Lorentz/Drude–Lorentz; VKK (variational, KK‑constrained).
- **EIS/equivalent circuits**: R, L, C, Warburg, CPE networks that are passive and stable.
- **Rational macromodels**: **Vector Fitting (VF)** followed by **passivity enforcement** (shift residues/poles to ensure \(\mathrm{Re}\,H(i\omega)\ge 0\) and stability). Compact, broadband, KK‑consistent models for \(Z(\omega)\), \(Y(\omega)\), or transfer functions.

---

## 7) Post‑Fit Validation

- **KK residual spectrum (recommended plot)**  
  Define the KK residual as
  \[
  r_{\mathrm{KK}}(\omega)= \text{measured real part} - \mathcal{K}[\text{measured imaginary part}],
  \]
  or vice‑versa, where \(\mathcal{K}[\cdot]\) is your KK operator (SSKK/VKK allowed).  
  Plot \(r_{\mathrm{KK}}(\omega)\) together with standard fit residuals. Small, structureless KK residuals indicate physical consistency.

- **Diagnose issues**  
  Structured residuals often point to: drift (low‑\(\omega\) slope anomalies), unmodeled inductance (high‑\(\omega\) imaginary rise), contact resistance, baseline offsets, or stitching errors between instruments.

- **Cross‑representation checks**  
  Validate consistency across \(Z^*, Y^*, M^*\) if relevant; failures in one domain can be more apparent than in another.

---

## 8) Uncertainty & Reproducibility

- **Propagate errors through KK**  
  Use bootstrap or Monte‑Carlo draws from measurement uncertainties; run the KK (or VKK/SSKK) for each draw; report confidence bands for the KK‑derived counterpart and for fitted parameters.

- **Report your conventions and tails (make it reproducible)**  
  Always list: sign convention; transformed quantity; frequency grid; extrapolation functions and parameters (e.g., Hagen–Rubens below \(\nu_0\), Drude to \(\nu_1\), constant \(\varepsilon(\infty)\) above \(\nu_2\)); whether SSKK/MSKK/VKK was used; and anchor points.

---

## 9) Two “How‑To” Workflows

### A) Finite‑band optics (reflectance‑only)
1. Stitch instruments & calibrations; estimate DC \(\sigma_0\) if metallic.  
2. Low‑\(\omega\) tail: Hagen–Rubens (metal) or static‑\(\varepsilon\) limit (insulator).  
3. High‑\(\omega\) tail: approach \(\varepsilon(\infty)\) (literature/ab‑initio).  
4. Apply **SSKK** to retrieve phase; compute \(n(\omega), k(\omega)\), then \(\varepsilon^*(\omega)\).  
5. Optional **VKK** refinement to fit \(R(\omega)\) and any ellipsometry simultaneously.  
6. Perform sum‑rule checks and plot KK residuals.

### B) EIS (impedance spectroscopy)
1. Quick passivity/positive‑real sanity checks; correct for cable inductance.  
2. Run **Lin‑KK** or **Z‑HIT** to screen data quality and identify drift/artefacts.  
3. Choose representation \(Z^*\), \(Y^*\), or \(M^*\) to separate processes.  
4. Fit a KK‑consistent model (equivalent circuit or VF + passivity enforcement).  
5. Plot **KK residual spectrum**; iterate measurement if failures persist.

---

## 10) Numerical Implementation Tips

- Use **Clenshaw–Curtis** or **tanh–sinh** quadrature for better behavior near singularities.
- Prefer **log‑frequency** grids; work in \(\omega\) (rad/s) to avoid \(2\pi\) confusion.
- **Precompute the discrete KK operator** on your grid; then KK becomes a fast matrix–vector multiply in optimizers.
- Keep a **unit test** that recovers KK pairs for known analytic models (Debye, Drude) on your grid.

---

## 11) KK Residual Checklist (for your paper/report)

- [ ] Fourier sign convention and transformed quantity clearly stated.  
- [ ] Extrapolation functions and anchor points listed.  
- [ ] Choice of KK variant (standard / SSKK / MSKK / VKK) documented.  
- [ ] Frequency grid and quadrature method documented.  
- [ ] KK residual spectrum plotted and discussed.  
- [ ] Uncertainty propagation (bands on KK‑derived counterpart and fitted parameters).  
- [ ] Cross‑representation consistency checked (if applicable).  
- [ ] Sum‑rule or conservation checks reported (if applicable).

---

## 12) Reporting Template (copy–paste & fill)

**Quantity & convention**  
- Fourier convention: \(e^{-i\omega t}\) / \(e^{+i\omega t}\)  
- Quantity transformed: \(\chi\) / \(\varepsilon\) / \(\sigma\) / \(Z\) / \(Y\) / \(M\)

**Measurement band**  
- \(\omega_{\min}\) … \(\omega_{\max}\), grid: log‑spaced (N = …), instruments: …

**Extrapolations**  
- Low‑\(\omega\): … (e.g., Hagen–Rubens; parameters …)  
- High‑\(\omega\): … (e.g., \(\varepsilon(\infty)=…\); approach by …)  
- Anchors for SSKK/MSKK: \(\{(\omega_a, f(\omega_a))\}\)

**KK variant & numerics**  
- Variant: standard / SSKK / MSKK / VKK  
- Quadrature: trapezoidal / Clenshaw–Curtis / tanh–sinh  
- PV treatment: diagonal removal + local interpolation  
- Precomputation: discrete KK operator matrix (Y/N)

**Validation**  
- KK residual RMS: … ; structure: …  
- Sum‑rules: …  
- Cross‑representation check: …  
- Uncertainty propagation: bootstrap \(N=\) … / MC …

**Model (if fitted)**  
- Family: Debye/Cole–Cole/Lorentz/Drude–Lorentz/VKK/VF+passivity  
- Parameters ± CI: …  
- Goodness‑of‑fit (not just KK): …

---

## 13) MATLAB Snippets

> These are minimal, self‑contained examples intended for log‑spaced grids over \(\omega>0\). They implement (i) a **discrete KK operator** for \(\mathrm{Re}\leftarrow\mathrm{Im}\) and (ii) **SSKK** with one anchor. Adapt as needed for your quantity and convention.

### 13.1 Discrete KK operator on an arbitrary grid
```matlab
function H = kk_kernel_Re_from_Im(omega)
% KK kernel matrix H such that Re ≈ H * Im (one-sided, e^{-iwt} convention).
% omega: column vector [rad/s], strictly increasing.
% Implements: Re f(wi) = (2/pi) PV ∫_0^∞ [ w' Im f(w')/(w'^2 - wi^2) ] dw'
% Principal value is handled by zeroing diagonal and using local interpolation.

omega = omega(:);
N = numel(omega);
H = zeros(N,N);

% Nonuniform trapezoid weights
dw = zeros(N,1);
dw(1)   = (omega(2)-omega(1));
dw(N)   = (omega(N)-omega(N-1));
for j = 2:N-1
    dw(j) = 0.5*(omega(j+1)-omega(j-1));
end

for i = 1:N
    wi = omega(i);
    for j = 1:N
        if i ~= j
            wj = omega(j);
            H(i,j) = (2/pi) * (wj / (wj^2 - wi^2)) * dw(j);
        end
    end
    % Optional small PV correction near diagonal:
    % Could add local linear interpolation to approximate the removed self-term.
end
end
```

**Usage**
```matlab
% Given frequency grid omega and measured Im_f:
H = kk_kernel_Re_from_Im(omega);
Re_from_KK = H * Im_f;   % Compare with measured Re_f
KK_residual = Re_measured - Re_from_KK;
```

### 13.2 Singly‑Subtractive KK (SSKK) with one anchor
```matlab
function Re_out = sskk_Re_from_Im(Im_f, omega, omega_a, Re_at_omega_a)
% Computes Re f(omega) using SSKK with one anchor (omega_a, Re_at_omega_a).
% Re(w) - Re(wa) = (2/pi) * (w^2 - wa^2) * PV ∫ [ w' Im(w') / ((w'^2 - w^2)(w'^2 - wa^2)) ] dw'

omega = omega(:); Im_f = Im_f(:);
N = numel(omega); Re_out = zeros(N,1);

% Precompute trapezoid weights on nonuniform grid
dw = zeros(N,1);
dw(1)   = (omega(2)-omega(1));
dw(N)   = (omega(N)-omega(N-1));
for j = 2:N-1
    dw(j) = 0.5*(omega(j+1)-omega(j-1));
end

for i = 1:N
    wi = omega(i);
    num = 0.0;
    for j = 1:N
        wj = omega(j);
        if abs(wj-wi) < 1e-12 || abs(wj-omega_a) < 1e-12
            continue; % PV skip singular points
        end
        num = num + ( wj * Im_f(j) ./ ((wj^2 - wi^2) * (wj^2 - omega_a^2)) ) * dw(j);
    end
    Re_out(i) = Re_at_omega_a + (2/pi) * (wi^2 - omega_a^2) * num;
end
end
```

**Usage**
```matlab
% Example anchor at omega_a (ideally inside the measured band):
[~, ia] = min(abs(omega - omega_a));
Re_anchor = Re_measured(ia);

Re_sskk = sskk_Re_from_Im(Im_measured, omega, omega(ia), Re_anchor);
```

> **Note:** Mirror the formulas appropriately if you want \(\mathrm{Im}\leftarrow\mathrm{Re}\). Always match your Fourier convention and quantity.

---

## 14) References & Further Reading (non‑exhaustive)
- Lucarini, L., et al., *Kramers–Kronig Relations in Optical Materials Research* (Springer).  
- Nussenzveig, H. M., *Causality and Dispersion Relations* (Academic Press).  
- Kuzmenko, A. B., “Kramers–Kronig constrained variational analysis of optical spectra.”  
- Boukamp, B. A., works on KK tests in EIS; Lin‑KK, Z‑HIT methods in the EIS literature.  
- Classic microwave/RF macromodelling: vector fitting and passivity enforcement.

---

## 15) Executive Summary (for readers in a hurry)

- KK is a **physics constraint** you can use at every stage: pre‑processing, fitting, validation.  
- Prefer **finite‑band cures** (SSKK/MSKK, VKK) before attempting plain KK with arbitrary tails.  
- Use KK to **seed parameters**, **enforce passivity**, and **screen models**.  
- Validate with a **KK residual spectrum** and propagate uncertainty through the transforms.  
- Report conventions, tails, anchors, and numerics so results are reproducible.
