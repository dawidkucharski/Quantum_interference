# MwTW 2026 Poster Review

## Quick assessment

The current text in `manuscript/Abstract-Template-MwTW2026.docx` is scientifically coherent and aligned with the manuscript, but in its present form it reads more like a journal abstract than a conference-poster abstract.

The two main issues are:

1. **It is too long** for a typical conference abstract. The extracted text is about **708 words**.
2. **The project status and poster take-away are not front-loaded enough**. The reader gets the message only after a long methodological build-up.

## What should be improved

### 1. Make the project stage explicit

The abstract should state very early that this is a:

- simulation-first benchmark,
- based on real measured FV `.sur` surfaces used as reference topographies,
- not yet a full laboratory demonstration of a quantum interferometer.

This matters because the manuscript itself explicitly states that the coincidence channel is still a phenomenological proxy rather than a full fourth-order experimental transfer model.

### 2. Remove the rhetorical opening

The current opening question is readable, but for a technical conference poster it is weaker than a direct statement of scope. It also risks sounding slightly promotional.

Prefer a first sentence that says what was compared and why.

### 3. Show the result split earlier

The strongest message of the project is not “quantum helps”, but:

- no universal quantum advantage,
- classical PSI remains best for fine texture and lowest RMSE,
- the hybrid strategy is the most defensible nonclassical outcome,
- the direct quantum-like branch is only selectively useful.

That should appear in the first half of the abstract, not only near the end.

### 4. Add 2-3 concrete numbers

For a poster submission, a few hard numbers make the current project status look much more mature. The manuscript already contains concise values worth quoting:

- Hybrid gives the lowest median `|ΔSa|`: **197.0 nm**.
- Quantum-like gives the lowest median `|ΔSq|`: **418.6 nm**.
- Quantum-like gives the lowest median `|ΔSz|`: **9498.0 nm**.
- Hybrid has the lowest median height RMSE in the bootstrap summary: **558.6 nm**.

### 5. End with a project-facing conclusion

For a poster, the last sentence should say what this means for the project direction:

- hybrid architecture is the main current outcome,
- next step is improving the coincidence model and moving toward experimental validation.

## Suggested title

Recommended technical title:

**Hybrid Quantum-Inspired Profilometry: A Benchmark on Measured Rough Surfaces**

If you want a slightly more question-driven title:

**Can Quantum-Inspired Coincidence Channels Improve Rough-Surface Profilometry?**

The first option is safer and sounds more mature.

## Proposed revised abstract

Quantum and quantum-inspired interferometric concepts are often proposed as routes to improved optical sensing, but their practical value for rough-surface profilometry remains unclear. This poster presents the current state of a simulation-first benchmarking project comparing classical four-step phase-shifting interferometry (PSI), direct coincidence-inspired reconstruction, and a hybrid coarse-to-fine strategy under matched count budgets. The benchmark combines controlled synthetic sweeps with real focus-variation (FV) microscopy topographies exported as `.sur` files, which are used as common reference surfaces for all simulated measurement channels. Performance is evaluated using detrended height RMSE, areal roughness errors (`Sa`, `Sq`, `Sz`), per-surface winner counts, and representative spatial-frequency fidelity.

The present results do not support a universal quantum advantage. Classical PSI remains the most reliable baseline for fine-texture recovery and lowest pointwise height error. Direct quantum-like reconstruction is only selectively useful, mainly for smoother finishing-style surfaces and chiefly for envelope-dominated descriptors such as `Sq` and `Sz`. The strongest nonclassical result is the hybrid strategy, in which coincidence-like information is used only as a coarse absolute-height prior while the final fine texture is preserved by the classical short-wavelength branch. In the measured-surface benchmark, the hybrid method gives the lowest median `|ΔSa|` (197.0 nm), while the direct quantum-like branch gives the lowest median `|ΔSq|` and `|ΔSz|` (418.6 nm and 9498.0 nm).

The main conclusion at the current project stage is architectural rather than promotional: coincidence-based sensing appears most promising as an auxiliary ambiguity-resolving channel inside a hybrid profilometer, not as a universal replacement for classical PSI. Ongoing work focuses on a more realistic coincidence model, stronger non-ideality analysis, and eventual experimental validation.

## Recommended poster structure

Use a simple six-block structure:

1. **Problem / gap**  
   No fair benchmark exists between classical PSI and coincidence-inspired channels on realistic rough surfaces.

2. **Aim**  
   Determine where a quantum-inspired channel should replace PSI, support PSI, or be avoided.

3. **Current project state**  
   Simulation-first framework is implemented and benchmarked on measured FV `.sur` surfaces.

4. **Methods**  
   Compare three branches: Classical, Quantum-like, Hybrid.

5. **Key results**  
   Classical best for fine texture; Hybrid best overall nonclassical option; Quantum-like selective for `Sq`/`Sz`.

6. **Next steps**  
   Full fourth-order model, stronger noise realism, experimental validation.

## Figures worth promoting on the poster

Best candidates already available in the repo:

- `outputs/paper_alicona_benchmark/figures/rmse_measured_summary.pdf`
- `outputs/paper_alicona_benchmark/figures/roughness_measured_summary.pdf`
- `manuscript/figures/tikz_layouts.tex`
- `manuscript/figures/tikz_method_selection.tex`

If space is limited, drop the PSD panel first and keep:

- one method schematic,
- one benchmark summary figure,
- one visual decision rule / take-home figure.

## What to avoid on the poster

- Do not imply an experimental quantum advantage if the current evidence is simulation-first.
- Do not lead with too much optical-detail text before stating the result.
- Do not overload the poster with tables; use 1 small metric box instead.
- Do not present the direct quantum-like branch as the default winner.