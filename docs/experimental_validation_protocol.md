# Reduced Experimental Validation Protocol

This document turns the manuscript's largest remaining acceptance blocker into an executable lab task. It does not replace the experiment. It defines the minimum reduced surface set, the measurement matrix, and the pass/fail questions that the experiment must answer.

The core design choice is deliberate: the measured-surface manuscript benchmark uses the long-effective-wavelength `diff` coincidence proxy as its default direct branch. The first experimental validation pass should therefore reproduce that branch and the associated hybrid coarse-prior workflow before expanding to the NOON-like branch used in the synthetic step-free sweep.

## 1. Regenerate the Reduced Subset

Run:

```bash
python scripts/select_experimental_validation_subset.py
```

This writes:

- `outputs/paper_alicona_benchmark/experimental_validation/validation_subset.csv`
- `outputs/paper_alicona_benchmark/experimental_validation/validation_subset.md`

The generated subset is split into:

- `core`: the minimum defensible lab set for the manuscript's main claims
- `extended`: two additional cases that test the strongest conditional exceptions in the paper

## 2. Experimental Objective

The reduced experiment is not trying to prove universal quantum advantage. It is trying to falsify or support five narrower manuscript claims:

1. A coincidence-derived coarse prior can improve fixed-workflow height fidelity in hybrid form.
2. Direct coincidence-only reconstruction can fail catastrophically even when classical and hybrid reconstructions remain well behaved.
3. The direct branch has limited treatment-specific exceptions that should be tested explicitly rather than inferred from pooled statistics.
4. Broad-envelope following is not uniquely nonclassical, because a classical two-colour synthetic-wavelength baseline can reproduce some of the same behaviour.
5. Detector non-idealities should hurt the direct coincidence branch more strongly than the hybrid branch.

## 3. Required Measurements Per Surface

For every surface in the `core` subset, acquire the following at the same lateral patch and as close as possible to the same spatial registration:

1. Reference surface map.
Use the existing FV map as the benchmark reference and reacquire the same patch if possible.
If available, add one independent cross-check instrument for at least a subset of surfaces: stylus, CSI, or another calibrated optical profiler.

2. Classical PSI baseline.
Acquire a 4-step reflective PSI stack at the manuscript short wavelength (`532 nm` nominal) with at least `5` independent repeats.

3. Classical two-colour control.
Acquire two classical PSI stacks at `810 nm` and `809 nm` with the same patch registration and repeat count. This is required for the non-uniqueness test.

4. Coincidence branch.
Acquire the direct coincidence measurement corresponding to the manuscript's `diff` branch at `810/809 nm`, again with at least `5` independent repeats.

5. Hybrid reconstruction inputs.
Store the wrapped short-wavelength classical phase and the direct coincidence-derived coarse height so the hybrid reconstruction can be reproduced offline exactly as in the manuscript.

For the `detector_fragility_case`, repeat the coincidence acquisition under at least one deliberately degraded detector setting, e.g. a wider coincidence window or induced efficiency imbalance, so the non-ideal sensitivity can be checked experimentally rather than only in simulation.

## 4. What to Record During Acquisition

For each repeat, record:

- surface stem and patch identifier
- illumination wavelength(s)
- phase-step sequence and nominal step values
- exposure/integration settings
- detector model and detector IDs
- coincidence gate time
- estimated singles rates and coincidence rate
- detector efficiencies if calibrated
- deadtime setting or inferred deadtime model
- ambient/background drift observations
- alignment notes and any visible decorrelation or fringe-loss events

These logs are not optional. They are required to connect the experimental result to the manuscript's current rate-model and drift arguments.

## 5. Primary Analysis Endpoints

Use the same endpoint hierarchy as the revised manuscript.

Primary endpoint:

- detrended height RMSE against the benchmark reference

Secondary diagnostics:

- matched-bandwidth `|ΔSa|` and `|ΔSq|`
- native-grid `|ΔSz|` only as an envelope-following diagnostic, not as the basis for a universal workflow claim
- residual maps
- radial PSD comparison on the common benchmark grid

If you cannot maintain common bandwidth between the experimental reconstruction and the reference, do not sell the roughness results as primary evidence.

## 6. Minimum Success Criteria

The experiment should be considered manuscript-supporting only if all of the following hold on the `core` subset:

1. Hybrid beats direct coincidence-only reconstruction on height RMSE for a majority of the core surfaces.
2. The `hybrid_best_height_case` and `hybrid_median_height_case` remain hybrid-favouring on height RMSE.
3. The `direct_q_catastrophic_failure_case` shows a clear image-domain failure in the direct branch that is not mirrored by both other branches.
4. The `classical_two_colour_nonuniqueness_case` shows that classical two-colour performance matches or exceeds direct coincidence on the broad-envelope diagnostic chosen for that case.
5. The `detector_fragility_case` shows a stronger non-ideal penalty for the direct coincidence branch than for the hybrid branch.

The rough-treatment exception cases are supportive, not mandatory. Their role is to test whether the limited grouped exceptions in the manuscript survive experimental acquisition.

## 7. Recommended Reporting Structure for the Revision

When the lab data exist, report them as a reduced validation study rather than as a full benchmark rerun.

Recommended subsection structure:

1. Experimental reduced subset and acquisition protocol
2. Registration and reference strategy
3. Height-RMSE validation on the core subset
4. Classical two-colour versus coincidence non-uniqueness check
5. Detector-fragility check on the designated subset case
6. Residual-map and PSD examples for one success case and one failure case

## 8. What This Protocol Does Not Solve

This protocol does not by itself close the fourth-order physics model, provide a full uncertainty budget, or replace public archival deposition. It is the minimum credible bridge from the current simulation benchmark to a reviewer-resistant experimental validation section.