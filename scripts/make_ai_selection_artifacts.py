#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
import warnings
from collections import defaultdict
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


METHOD_ORDER = ["classical", "quantum_like", "hybrid"]
METHOD_LABEL = {
    "classical": "Classical",
    "quantum_like": "Quantum-like",
    "hybrid": "Hybrid",
}

ENDPOINT_SPECS = [
    ("height_rmse", "Height RMSE", "height_rmse_nm", False, "Height RMSE"),
    ("abs_bias_Sa", r"$|\Delta S_a|$", "bias_Sa_nm", True, r"$|\Delta S_a|$"),
    ("abs_bias_Sq", r"$|\Delta S_q|$", "bias_Sq_nm", True, r"$|\Delta S_q|$"),
    ("abs_bias_Sz", r"$|\Delta S_z|$", "bias_Sz_nm", True, r"$|\Delta S_z|$"),
]

ROW_END = "\\\\"


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def _collapse_surface_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, float | str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["stem"]), str(row["method"]))].append(row)

    out: dict[str, dict[str, dict[str, float | str]]] = defaultdict(dict)
    for (stem, method), entries in grouped.items():
        if method not in METHOD_ORDER:
            continue
        n_entries = float(len(entries))
        out[stem][method] = {
            "material": str(entries[0]["material"]),
            "treatment": str(entries[0]["treatment"]),
            "Sa_true_nm": sum(float(entry["Sa_true_nm"]) for entry in entries) / n_entries,
            "Sq_true_nm": sum(float(entry["Sq_true_nm"]) for entry in entries) / n_entries,
            "Sz_true_nm": sum(float(entry["Sz_true_nm"]) for entry in entries) / n_entries,
            "height_rmse_nm": sum(float(entry["height_rmse_nm"]) for entry in entries) / n_entries,
            "bias_Sa_nm": sum(float(entry["bias_Sa_nm"]) for entry in entries) / n_entries,
            "bias_Sq_nm": sum(float(entry["bias_Sq_nm"]) for entry in entries) / n_entries,
            "bias_Sz_nm": sum(float(entry["bias_Sz_nm"]) for entry in entries) / n_entries,
        }
    return dict(out)


def _best_method_and_margin(
    method_map: dict[str, dict[str, float | str]],
    *,
    metric_key: str,
    use_abs: bool,
) -> tuple[str, float, float, float]:
    scored: list[tuple[float, str]] = []
    for method in METHOD_ORDER:
        values = method_map.get(method)
        if values is None:
            continue
        value = float(values[metric_key])
        if use_abs:
            value = abs(value)
        scored.append((value, method))

    if len(scored) < 2:
        raise ValueError("Need at least two methods to define a decision target")

    scored.sort(key=lambda item: (item[0], METHOD_ORDER.index(item[1])))
    best_value, best_method = scored[0]
    second_best_value, _ = scored[1]
    return best_method, best_value, second_best_value, second_best_value - best_value


def _build_decision_rows(
    surface_map: dict[str, dict[str, dict[str, float | str]]]
) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for stem, method_map in sorted(surface_map.items()):
        if len(method_map) < 2:
            continue
        reference = next(iter(method_map.values()))
        sa_true = float(reference["Sa_true_nm"])
        sq_true = float(reference["Sq_true_nm"])
        sz_true = float(reference["Sz_true_nm"])
        for endpoint_key, endpoint_name, metric_key, use_abs, _ in ENDPOINT_SPECS:
            best_method, best_value, second_best_value, margin_to_second = _best_method_and_margin(
                method_map,
                metric_key=metric_key,
                use_abs=use_abs,
            )
            rows.append(
                {
                    "stem": stem,
                    "material": str(reference["material"]),
                    "treatment": str(reference["treatment"]),
                    "Sa_true_nm": sa_true,
                    "Sq_true_nm": sq_true,
                    "Sz_true_nm": sz_true,
                    "log_Sa_true_nm": math.log10(max(sa_true, 1e-9)),
                    "log_Sq_true_nm": math.log10(max(sq_true, 1e-9)),
                    "log_Sz_true_nm": math.log10(max(sz_true, 1e-9)),
                    "endpoint_key": endpoint_key,
                    "endpoint_name": endpoint_name,
                    "target_method": best_method,
                    "target_method_label": METHOD_LABEL[best_method],
                    "best_value_nm": best_value,
                    "second_best_value_nm": second_best_value,
                    "margin_to_second_nm": margin_to_second,
                }
            )
    return rows


def _prepare_features(
    decision_rows: list[dict[str, str | float]]
) -> tuple[list[list[float | str]], list[str], list[str], list[str]]:
    features: list[list[float | str]] = []
    labels: list[str] = []
    groups: list[str] = []
    endpoints: list[str] = []
    for row in decision_rows:
        features.append(
            [
                float(row["log_Sa_true_nm"]),
                float(row["log_Sq_true_nm"]),
                float(row["log_Sz_true_nm"]),
                str(row["endpoint_key"]),
                str(row["material"]),
                str(row["treatment"]),
            ]
        )
        labels.append(str(row["target_method"]))
        groups.append(str(row["stem"]))
        endpoints.append(str(row["endpoint_key"]))
    return features, labels, groups, endpoints


def _build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                [0, 1, 2],
            ),
            ("cat", OneHotEncoder(handle_unknown="ignore"), [3, 4, 5]),
        ]
    )


def _model_specs(seed: int) -> list[tuple[str, object]]:
    return [
        ("Majority baseline", DummyClassifier(strategy="most_frequent")),
        ("Multinomial logistic", LogisticRegression(max_iter=5000, class_weight="balanced")),
        (
            "Random forest",
            RandomForestClassifier(
                n_estimators=300,
                random_state=seed,
                class_weight="balanced_subsample",
                min_samples_leaf=2,
            ),
        ),
    ]


def _evaluate_models(
    decision_rows: list[dict[str, str | float]],
    *,
    seed: int,
) -> tuple[list[dict[str, str | float]], dict[str, list[str]]]:
    features, labels, groups, endpoints = _prepare_features(decision_rows)
    preprocessor = _build_preprocessor()
    logo = LeaveOneGroupOut()

    results: list[dict[str, str | float]] = []
    predictions: dict[str, list[str]] = {}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for model_name, model in _model_specs(seed):
            pipeline = Pipeline([("pre", preprocessor), ("clf", model)])
            fold_predictions = [
                str(item)
                for item in cross_val_predict(
                    pipeline,
                    features,
                    labels,
                    cv=logo.split(features, labels, groups=groups),
                )
            ]
            result: dict[str, str | float] = {
                "model": model_name,
                "accuracy": accuracy_score(labels, fold_predictions),
                "balanced_accuracy": balanced_accuracy_score(labels, fold_predictions),
                "macro_f1": f1_score(labels, fold_predictions, average="macro"),
            }
            for endpoint_key, _, _, _, _ in ENDPOINT_SPECS:
                idx = [i for i, value in enumerate(endpoints) if value == endpoint_key]
                result[f"accuracy_{endpoint_key}"] = accuracy_score(
                    [labels[i] for i in idx],
                    [fold_predictions[i] for i in idx],
                )
            results.append(result)
            predictions[model_name] = fold_predictions
    return results, predictions


def _write_csv(path: Path, rows: list[dict[str, str | float]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_decision_dataset(path: Path, decision_rows: list[dict[str, str | float]]) -> None:
    fieldnames = [
        "stem",
        "material",
        "treatment",
        "Sa_true_nm",
        "Sq_true_nm",
        "Sz_true_nm",
        "log_Sa_true_nm",
        "log_Sq_true_nm",
        "log_Sz_true_nm",
        "endpoint_key",
        "endpoint_name",
        "target_method",
        "target_method_label",
        "best_value_nm",
        "second_best_value_nm",
        "margin_to_second_nm",
    ]
    _write_csv(path, decision_rows, fieldnames)


def _write_model_comparison(path: Path, results: list[dict[str, str | float]]) -> None:
    fieldnames = ["model", "accuracy", "balanced_accuracy", "macro_f1"] + [
        f"accuracy_{endpoint_key}" for endpoint_key, _, _, _, _ in ENDPOINT_SPECS
    ]
    _write_csv(path, results, fieldnames)


def _write_predictions(
    path: Path,
    *,
    decision_rows: list[dict[str, str | float]],
    model_name: str,
    predictions: list[str],
) -> None:
    rows: list[dict[str, str | float]] = []
    for decision_row, predicted_method in zip(decision_rows, predictions):
        row = dict(decision_row)
        row["selected_model"] = model_name
        row["predicted_method"] = predicted_method
        row["predicted_method_label"] = METHOD_LABEL[predicted_method]
        row["is_correct"] = int(predicted_method == str(decision_row["target_method"]))
        rows.append(row)
    fieldnames = [
        "stem",
        "material",
        "treatment",
        "endpoint_key",
        "endpoint_name",
        "target_method",
        "target_method_label",
        "predicted_method",
        "predicted_method_label",
        "is_correct",
        "Sa_true_nm",
        "Sq_true_nm",
        "Sz_true_nm",
        "log_Sa_true_nm",
        "log_Sq_true_nm",
        "log_Sz_true_nm",
        "best_value_nm",
        "second_best_value_nm",
        "margin_to_second_nm",
        "selected_model",
    ]
    _write_csv(path, rows, fieldnames)


def _format_metric(value: float) -> str:
    return f"${value:.3f}$"


def _write_table(
    path: Path,
    *,
    results: list[dict[str, str | float]],
    label: str,
    n_surfaces: int,
    n_decisions: int,
) -> None:
    lines = [
        "% Auto-generated by scripts/make_ai_selection_artifacts.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{4pt}",
        (
            "\\caption{Exploratory AI-assisted method-selection proof-of-concept derived from the "
            "measured-surface benchmark. Each measured surface contributes four decision samples, one "
            "for each endpoint, yielding "
            f"{n_decisions} surface-endpoint decisions from {n_surfaces} measured surfaces. "
            "Evaluation uses leave-one-surface-out cross-validation so all endpoints from a held-out "
            "surface are excluded together. Features are restricted to observable descriptors available "
            "before reconstruction: material, treatment, and the FV-derived roughness levels $S_a$, "
            "$S_q$, and $S_z$.}"
        ),
        f"\\label{{{label}}}",
        "\\resizebox{\\textwidth}{!}{%",
        "\\begin{tabular}{lcccccc}",
        "\\toprule",
        "Model & Overall acc. & Macro-$F_1$ & Height RMSE & $|\\Delta S_a|$ & $|\\Delta S_q|$ & $|\\Delta S_z|$ " + ROW_END,
        "\\midrule",
    ]
    for result in results:
        row = [
            str(result["model"]),
            _format_metric(float(result["accuracy"])),
            _format_metric(float(result["macro_f1"])),
        ]
        for endpoint_key, _, _, _, _ in ENDPOINT_SPECS:
            row.append(_format_metric(float(result[f"accuracy_{endpoint_key}"])))
        lines.append(" & ".join(row) + " " + ROW_END)
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "}%",
            "\\end{table}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Create AI method-selection proof-of-concept artefacts from per_surface.csv")
    ap.add_argument("--per-surface", type=Path, default=Path("outputs/paper_alicona_benchmark/per_surface.csv"))
    ap.add_argument("--outdir", type=Path, default=Path("outputs/paper_alicona_benchmark/ai_selection"))
    ap.add_argument("--out-table", type=Path, default=Path("manuscript/tables/ai_method_selection.tex"))
    ap.add_argument("--label", type=str, default="tab:ai_method_selection")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    surface_map = _collapse_surface_rows(_load_rows(args.per_surface))
    decision_rows = _build_decision_rows(surface_map)
    results, predictions = _evaluate_models(decision_rows, seed=int(args.seed))
    best_result = max(results, key=lambda row: (float(row["macro_f1"]), float(row["accuracy"])))
    best_model_name = str(best_result["model"])

    _write_decision_dataset(args.outdir / "decision_dataset.csv", decision_rows)
    _write_model_comparison(args.outdir / "model_comparison.csv", results)
    _write_predictions(
        args.outdir / "best_model_predictions.csv",
        decision_rows=decision_rows,
        model_name=best_model_name,
        predictions=predictions[best_model_name],
    )
    _write_table(
        args.out_table,
        results=results,
        label=str(args.label),
        n_surfaces=len(surface_map),
        n_decisions=len(decision_rows),
    )
    print(f"Wrote: {args.outdir / 'decision_dataset.csv'}")
    print(f"Wrote: {args.outdir / 'model_comparison.csv'}")
    print(f"Wrote: {args.outdir / 'best_model_predictions.csv'}")
    print(f"Wrote: {args.out_table}")
    print(f"Best model: {best_model_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())