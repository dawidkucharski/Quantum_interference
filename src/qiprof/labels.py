from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SurLabel:
    stem: str
    sample_group: str
    material_code: str
    treatment_code: str
    material_en: str
    treatment_en: str


# --- Material code mapping (filename -> English) ---
# Keep this conservative: map what is clear, otherwise fall back to the code.
MATERIAL_CODE_TO_EN: Dict[str, str] = {
    "1.4301": "Stainless steel 1.4301 (AISI 304)",
    "C45": "Steel C45",
    # Aluminium: treat all aluminium codes as Aluminium 7075 for reporting
    "AL": "Aluminium 7075",
    "Al": "Aluminium 7075",
    "Al7075": "Aluminium 7075",
    "AL7075": "Aluminium 7075",
    "AL70752": "Aluminium 7075",

    # Titanium: simplify to Titanium
    "Ti": "Titanium",
    "Ti6A14V": "Titanium",

    "Graphite": "Graphite",
    # Brass: simplify all brass codes to Brass
    "Mosiadz": "Brass",
    "MO58A": "Brass",
    # Project-specific code: user stated ELLOR is graphite
    "ELLOR": "Graphite",
}


# --- Treatment code mapping (suffix tokens -> English) ---
# Notes:
# - 'wyk' = wykańczające (finishing)
# - 'zgrub' / 'zgru' = zgrubne (roughing)
TREATMENT_CODE_TO_EN: Dict[str, str] = {
    # General surface treatments
    "szlifowane": "Grinding",
    "szkielkowane": "Glass bead blasted",
    "oselkowane": "Honed",

    # Turning (toczenie)
    "t_wyk": "Turning (finishing)",
    "t_zgrub": "Turning (roughing)",
    "t_zgrubne": "Turning (roughing)",
    "t.zgrub": "Turning (roughing)",

    # Milling (frezowanie)
    "frez_wyk": "Milling (finishing)",
    "frez_zgr": "Milling (roughing)",
    "frez_zgrub": "Milling (roughing)",
    "frez_zgrubne": "Milling (roughing)",

    # WEDM (wire EDM)
    "wedm_wyk": "Wire EDM (finishing)",
    "wedm_zgru": "Wire EDM (roughing)",
    "wedm_zgr": "Wire EDM (roughing)",
    "wedm_zgru_1prz": "Wire EDM (roughing)",

    # Burnishing (nagniatanie)
    "nagniat": "Burnishing",
}


def _normalize_token(s: str) -> str:
    return (
        s.strip()
        .replace(" ", "")
        .replace("\t", "")
        .replace("__", "_")
        .replace("..", ".")
    )


def decode_sur_stem(stem: str) -> SurLabel:
    """Decode a `.sur` filename stem into English material/treatment labels.

    Expected examples:
    - ELLOR_t_wyk
    - 1.4301_szlifowane
    - P1-AL7075_frez_wyk

    Returns both the original codes and English labels.
    """

    stem_n = _normalize_token(stem)

    # Split material vs treatment by first underscore.
    if "_" in stem_n:
        material_part, treatment_part = stem_n.split("_", 1)
    else:
        material_part, treatment_part = stem_n, ""

    # Optional sample group prefix like 'P1-...'
    sample_group = ""
    material_code = material_part
    if "-" in material_part:
        prefix, rest = material_part.split("-", 1)
        if prefix and rest and prefix.upper().startswith("P"):
            sample_group = prefix
            material_code = rest

    # Some files encode the treatment after a '-' instead of '_' (or in addition to it).
    # Example: P1-1.4301-t.zgrub.sur
    treatment_code = treatment_part
    if "-" in material_code:
        head, tail = material_code.split("-", 1)
        if head in MATERIAL_CODE_TO_EN or head.replace(" ", "") in MATERIAL_CODE_TO_EN:
            material_code = head
            treatment_code = tail if not treatment_code else f"{tail}_{treatment_code}"
    material_en = MATERIAL_CODE_TO_EN.get(material_code, material_code)
    treatment_en = TREATMENT_CODE_TO_EN.get(treatment_code, treatment_code)

    return SurLabel(
        stem=stem,
        sample_group=sample_group,
        material_code=material_code,
        treatment_code=treatment_code,
        material_en=material_en,
        treatment_en=treatment_en,
    )
