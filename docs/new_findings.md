# New findings to target (metrology impact)

This project will only matter (metrologically) if we can produce **regime maps** with clear, quantitative claims.

## Finding 1 — Tunability has a tradeoff (unambiguous range vs texture sensitivity)
Synthetic wavelength:

$$\Lambda = \frac{\lambda_1\lambda_2}{|\lambda_1-\lambda_2|}$$

- Larger $\Lambda$ increases unambiguous height range and makes step/fringe-order problems easier.
- But larger $\Lambda$ reduces phase modulation from nm-scale texture: $\phi \propto h/\Lambda$.

**Publishable result:** show an *optimal* $\Lambda$ (or optimal $(\lambda_1,\lambda_2)$) given a fixed pair budget, where step errors decrease but texture RMSE increases.

What to report:
- `rmse_h_nm` (texture-focused, after plane detrend)
- `step_err_nm` (discontinuity-focused)
- both as functions of $\Lambda$ and photon/pair budget

## Finding 2 — Hybrid coarse-to-fine unwrapping is the “new way”
Use quantum-like synthetic wavelength only as a *coarse* channel to disambiguate fringe order, then recover fine texture with classical PSI.

Implementation in this repo:
- Coarse height: quantum-like coincidence PSI at $\Lambda$
- Fine phase: classical PSI at $\lambda_{class}$
- Hybrid unwrap: choose fringe order $k$ so $h_{class}+k\,\lambda_{class}/2$ matches coarse height (optionally smoothed)

**Publishable result:** hybrid reduces unwrap/step errors without sacrificing classical texture metrics.

What to report:
- step error (`step_err_nm`) improvement vs classical
- roughness bias (`bias_Sa_nm`, `bias_Sq_nm`) stays near classical

## Finding 3 — Robustness to practical non-idealities
Benchmarks under:
- phase-step errors (`--phase-step-sigma-deg`)
- background drift (`--background-drift-frac`)
- amplitude drift (`--amplitude-drift-frac`)

**Publishable result:** quantify sensitivity slopes (error vs drift), and show where hybrid helps.

## Recommended benchmark runs

1) Step-focused regime map (hybrid should win):
- Sweep step heights up to microns and use a large $\Lambda$.

2) Texture-focused regime map (classical should win):
- Small/no steps, moderate $\Lambda$, higher pair budget.

3) Tunability sweep:
- Fix pair budget and scan `lambda2` to vary $\Lambda$, plot `rmse_h_nm` and `step_err_nm`.
