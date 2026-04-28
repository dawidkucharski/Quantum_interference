# Reviewer #2 Point-by-Point Rebuttal

## Scope of This Response

This response is written against the current revised manuscript state, not against the older over-claiming draft.

The strategy of the revision was deliberate:

- not to defend weak validation language;
- not to hide the self-reference of the FV-seeded simulation branch;
- not to keep mixed roughness bandwidth bases in the main paper;
- not to imply uniquely quantum benefit where a stronger classical control reproduces the same direct-branch behaviour.

Instead, the manuscript was narrowed to a pre-validation benchmark, the surviving evidence was restricted to benchmark-grid height fidelity plus qualified diagnostics, and the experimental closure requirements were made explicit and mandatory.

## Numerical Consistency Check

No new recalculation was required for this rebuttal package.

Before drafting this response, the current manuscript values were checked against the existing generated artefacts and found to be internally consistent:

- Hybrid measured-surface height RMSE `314.0 nm`: [main.tex:112](../manuscript/main.tex#L112), [benchmark_bootstrap_ci.tex:13](../manuscript/tables/benchmark_bootstrap_ci.tex#L13)
- Classical-frontier oracle `559.1 nm` versus hybrid `314.0 nm`: [main.tex:112](../manuscript/main.tex#L112), [classical_frontier_control.tex:13](../manuscript/tables/classical_frontier_control.tex#L13)
- Rate-model control `290.9 / 1308.3 / 376.3 nm`: [main.tex:112](../manuscript/main.tex#L112), [benchmark_rate_model_control.tex:13](../manuscript/tables/benchmark_rate_model_control.tex#L13)
- Treatment holdout rates `70.0 / 60.0 / 60.0%`: [main.tex:112](../manuscript/main.tex#L112), [benchmark_holdout_treatment.tex:14](../manuscript/tables/benchmark_holdout_treatment.tex#L14), [benchmark_holdout_treatment.tex:15](../manuscript/tables/benchmark_holdout_treatment.tex#L15), [benchmark_holdout_treatment.tex:16](../manuscript/tables/benchmark_holdout_treatment.tex#L16)
- Matched-bandwidth `|ΔSz|` tolerance exceedance `42.4%`: [main.tex:112](../manuscript/main.tex#L112), [benchmark_tolerance_rates.tex:15](../manuscript/tables/benchmark_tolerance_rates.tex#L15)

Accordingly, this rebuttal required no additional recomputation before writing.

## 1. Reviewer Concern: “This is not validation; it is an internal self-consistency loop.”

### Response

We agree.

The revised manuscript no longer presents the measured-surface branch as validation of absolute interferometric performance. The title, abstract, introduction, methods, results, limitations, and conclusions now all state that the FV-seeded branch is a pre-validation or internal-consistency screening benchmark.

### Revised locations

- Title reframed to pre-validation benchmark: [main.tex:86](../manuscript/main.tex#L86)
- Abstract states the measured-surface branch is “not a metrological validation study”: [main.tex:112](../manuscript/main.tex#L112)
- Introduction states FV-seeded simulation “cannot validate absolute interferometric performance”: [main.tex:175](../manuscript/main.tex#L175)
- Contribution paragraph limits the paper to experimental prioritisation, not deployment or validation: [main.tex:178](../manuscript/main.tex#L178)
- Results section states the measured-surface branch “cannot validate absolute interferometric performance”: [main.tex:298](../manuscript/main.tex#L298)
- Limitations section states this is a “pre-validation simulation study” and not an external validation study: [main.tex:522](../manuscript/main.tex#L522)
- Conclusions state that none of the results substitute for independent metrological validation: [main.tex:530](../manuscript/main.tex#L530)

### What changed substantively

- Validation language was removed rather than defended.
- The paper now claims only benchmark-grid architectural screening value.
- The experimental follow-up is no longer optional future work but a stated closure requirement.

### Residual status

This concern is not experimentally closed in the current paper, because no new lab data were added. It is resolved at the manuscript-logic level by removing false validation framing and by making experimental validation the mandatory next step.

## 2. Reviewer Concern: “The roughness comparison is metrologically inconsistent because bandwidth bases are mixed.”

### Response

We agree.

The revised manuscript now uses matched-bandwidth benchmark-grid roughness as the only primary manuscript basis. Native-grid FV roughness is retained only as a harsher diagnostic stress test, never as a co-equal ranking basis.

### Revised locations

- Methods: benchmark-grid roughness made primary and native-grid roughness demoted to diagnostic: [main.tex:189](../manuscript/main.tex#L189)
- Results: primary roughness endpoints explicitly moved to the benchmark grid: [main.tex:298](../manuscript/main.tex#L298)
- Matched-bandwidth roughness promoted in the main figure caption: [main.tex:325](../manuscript/main.tex#L325)
- Limitations explicitly state that benchmark-grid descriptors are the only defensible primary basis: [main.tex:522](../manuscript/main.tex#L522)
- Failure taxonomy now includes “Reference-bandwidth mismatch”: [failure_taxonomy.tex:14](../manuscript/tables/failure_taxonomy.tex#L14)

### Supporting artefacts

- Bootstrap summary caption now states roughness endpoints use the matched-bandwidth benchmark-grid reference: [benchmark_bootstrap_ci.tex:6](../manuscript/tables/benchmark_bootstrap_ci.tex#L6)
- Treatment holdout table uses the matched-bandwidth basis: [benchmark_holdout_treatment.tex:6](../manuscript/tables/benchmark_holdout_treatment.tex#L6)
- Tolerance rates are benchmark-grid referenced: [benchmark_tolerance_rates.tex:6](../manuscript/tables/benchmark_tolerance_rates.tex#L6)

### Residual status

The revision closes the manuscript inconsistency. It does not transform FV roughness into traceable roughness metrology, and the paper no longer claims that it does.

## 3. Reviewer Concern: “The PSD comparison is overstated because the reference PSD is the simulator input.”

### Response

We agree.

The revised manuscript now says this explicitly. The PSD figure is no longer used rhetorically as independent validation; it is identified as an internal benchmark-grid spectral-consistency diagnostic.

### Revised locations

- Shared benchmark surface described explicitly: [main.tex:211](../manuscript/main.tex#L211)
- PSD text now states the reference is the same benchmark surface used to drive the forward model: [main.tex:373](../manuscript/main.tex#L373)
- PSD caption now states the figure is not an independent spectral validation: [main.tex:378](../manuscript/main.tex#L378)
- Failure taxonomy now includes the shared-prior self-reference and bandwidth mismatch failure modes: [failure_taxonomy.tex:13](../manuscript/tables/failure_taxonomy.tex#L13), [failure_taxonomy.tex:14](../manuscript/tables/failure_taxonomy.tex#L14)

### Residual status

This concern is resolved by explicit claim restriction, not by pretending the spectral comparison is stronger than it is.

## 4. Reviewer Concern: “The forward model is too idealized for a metrology paper.”

### Response

We largely agree.

The revision does not claim that the present simulator is a laboratory-calibrated fourth-order interferometer. Instead, the paper now states that the coincidence branch remains a proxy model, that the rate-based study is only a sensitivity study, and that experimental closure requires a grounded fourth-order transfer function.

### Revised locations

- Contribution framing restricts the paper to proxy-benchmark logic: [main.tex:178](../manuscript/main.tex#L178)
- Coincidence model remains explicitly proxy-level in the methods: [main.tex:234](../manuscript/main.tex#L234)
- Limitations state the coincidence branch is not validated against a laboratory fourth-order transfer function: [main.tex:522](../manuscript/main.tex#L522)
- Conclusions require replacement of the proxy hierarchy with an experimentally grounded fourth-order transfer function: [main.tex:532](../manuscript/main.tex#L532)

### Supporting artefacts

- Rate-model control numbers cited in the revised abstract and conclusions are consistent with the generated table: [benchmark_rate_model_control.tex:13](../manuscript/tables/benchmark_rate_model_control.tex#L13)

### Residual status

This concern is not experimentally solved in the present revision. It is answered by removing any suggestion that the proxy model already constitutes realistic metrological validation.

## 5. Reviewer Concern: “The quantum language is overstated because a classical two-colour control reproduces the key direct-branch effect.”

### Response

We agree.

The revised paper no longer treats the direct long-wavelength behaviour as uniquely quantum. It now states that the direct effect is not quantum-specific, that broad-envelope following alone does not justify a quantum claim, and that the only defensible surviving result is an architectural one at the hybrid level.

### Revised locations

- Abstract: “not uniquely nonclassical”: [main.tex:112](../manuscript/main.tex#L112)
- Methods: classical two-colour control introduced specifically to separate generic synthetic-wavelength behaviour from coincidence effects: [main.tex:280](../manuscript/main.tex#L280)
- Results: direct long-Λ behaviour stated to be “largely not quantum-specific”: [main.tex:365](../manuscript/main.tex#L365)
- Discussion: classical two-colour control used to reject the direct-branch quantum overclaim: [main.tex:495](../manuscript/main.tex#L495)
- Discussion: “broad-envelope following alone does not justify a quantum claim”: [main.tex:513](../manuscript/main.tex#L513)
- Conclusions: surviving direct long-Λ behaviour explicitly described as not uniquely quantum: [main.tex:530](../manuscript/main.tex#L530)

### Supporting artefacts

- Classical-frontier control keeps hybrid ahead on fixed-workflow height RMSE while weakening blanket hybrid roughness claims: [classical_frontier_control.tex:13](../manuscript/tables/classical_frontier_control.tex#L13)

### Residual status

The revised manuscript no longer asks the reviewer to accept a quantum-advantage claim on the basis of the current simulation evidence.

## 6. Reviewer Concern: “The uncertainty treatment is descriptive, not metrological.”

### Response

We agree.

The revision now says this directly. Bootstrap intervals, paired effects, and holdouts are retained as descriptive summaries of the fixed simulator/reference dataset, not as GUM-style uncertainty budgets or inter-instrument reproducibility studies.

### Revised locations

- Results retain bootstrap and holdout summaries but keep them descriptive: [main.tex:346](../manuscript/main.tex#L346)
- Discussion explicitly reclassifies the contribution as a screening benchmark rather than instrument-selection proof: [main.tex:505](../manuscript/main.tex#L505)
- Limitations state that bootstrap intervals, paired effects, and holdouts are not metrological uncertainty budgets: [main.tex:524](../manuscript/main.tex#L524)

### Supporting artefacts

- Bootstrap table remains clearly descriptive: [benchmark_bootstrap_ci.tex:6](../manuscript/tables/benchmark_bootstrap_ci.tex#L6)
- Treatment holdout fragility is documented numerically rather than hidden: [benchmark_holdout_treatment.tex:14](../manuscript/tables/benchmark_holdout_treatment.tex#L14), [benchmark_holdout_treatment.tex:15](../manuscript/tables/benchmark_holdout_treatment.tex#L15), [benchmark_holdout_treatment.tex:16](../manuscript/tables/benchmark_holdout_treatment.tex#L16)
- Tolerance failure rate for matched-bandwidth `|ΔSz|` remains explicit at `42.4%`: [benchmark_tolerance_rates.tex:15](../manuscript/tables/benchmark_tolerance_rates.tex#L15)

### Residual status

This criticism is not neutralized by statistical rhetoric. The manuscript now acknowledges the limited evidential status of these summaries.

## 7. Reviewer Concern: “The manuscript contains internal contradictions about validation and truth.”

### Response

We agree, and these contradictions were removed.

### Revised locations

- Title and abstract now use pre-validation language: [main.tex:86](../manuscript/main.tex#L86), [main.tex:112](../manuscript/main.tex#L112)
- The former “ground-truth surface” wording was replaced by “measured benchmark surface”: [main.tex:211](../manuscript/main.tex#L211)
- The old native-grid-main-benchmark wording was replaced by a benchmark-grid-primary roughness description: [main.tex:189](../manuscript/main.tex#L189), [main.tex:298](../manuscript/main.tex#L298)
- “Validation” was removed from author contributions: [main.tex:569](../manuscript/main.tex#L569)

### Residual status

This concern is textually closed in the present revision.

## 8. Reviewer Concern: “The paper still lacks a credible closure path for reference checking and archival reproducibility.”

### Response

We agree.

The revision now makes these closure steps mandatory rather than optional.

### Revised locations

- Main text requires a mandatory independent reference cross-check on every core validation case: [main.tex:517](../manuscript/main.tex#L517)
- Limitations state that experimental validation, an independent reference chain, and an archival reduced-data release are still required: [main.tex:524](../manuscript/main.tex#L524)
- Conclusions make persistent archival deposition mandatory for any stronger validation claim: [main.tex:532](../manuscript/main.tex#L532)
- Data availability statement now says clearly that the current materials are not yet a DOI-bearing archival experimental validation package: [main.tex:578](../manuscript/main.tex#L578)

### Supporting artefacts

- Reduced subset caption requires independent reference checking on every core case: [experimental_validation_subset.tex:6](../manuscript/tables/experimental_validation_subset.tex#L6)
- Protocol renamed and upgraded to revision-closure document: [experimental_validation_protocol.md:1](experimental_validation_protocol.md#L1)
- Mandatory resubmission gates added: [experimental_validation_protocol.md:7](experimental_validation_protocol.md#L7)
- Independent reference measurement required for every core surface: [experimental_validation_protocol.md:12](experimental_validation_protocol.md#L12), [experimental_validation_protocol.md:51](experimental_validation_protocol.md#L51)

### Residual status

This concern is not experimentally closed by the present manuscript, but the revision now prevents the paper from pretending otherwise.

## Bottom-Line Position of the Revision

The revised manuscript does not argue that the reviewer’s strongest metrology criticisms were wrong.

It argues something narrower and more defensible:

- the original validation-style framing was too strong;
- the main manuscript roughness basis had to be reduced to matched-bandwidth benchmark-grid descriptors;
- PSD and roughness comparisons derived from the shared FV prior had to be reclassified as internal diagnostics rather than validation;
- the direct long-wavelength effect is not uniquely quantum once the classical two-colour control is included;
- the only claim that survives intact is a fixed-workflow hybrid advantage for benchmark-grid height fidelity inside the present proxy benchmark;
- any stronger validation, traceability, or quantum-metrology claim now explicitly depends on the reduced experimental campaign, independent reference measurements, and persistent archival release.

That is the revision’s answer to Reviewer #2: not rhetorical resistance, but claim contraction to the portion of the evidence that remains defensible.