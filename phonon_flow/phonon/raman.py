"""Raman activity analysis from phonon irreducible representations.

Analyzes the Gamma-point phonon modes to determine which are Raman-active
based on the space group's character table.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from phonon_flow.constants import THZ_TO_CM1


# Raman activity by space group symmetry
# Keys: space group → list of Raman-active irreducible representations
# Format: each mode is (irrep_label, irrep_type)
# irrep_type: 'R' = Raman-active, 'IR_x/y/z' = IR-active, 'A' = acoustic, 'S' = silent

RAMAN_ACTIVE_IRREPS: Dict[int, Dict[str, List[str]]] = {
    62: {  # Pnma (D2h^16)
        "raman": ["Ag", "B1g", "B2g", "B3g"],
        "ir": ["B1u (x)", "B2u (y)", "B3u (z)"],
        "acoustic": ["B1u", "B2u", "B3u"],
    },
    139: {  # I4/mmm
        "raman": ["A1g", "B1g", "B2g", "Eg"],
        "ir": ["A2u (z)", "Eu (x,y)"],
        "acoustic": ["A2u", "Eu"],
    },
    225: {  # Fm-3m
        "raman": ["T2g"],
        "ir": ["T1u"],
        "acoustic": ["T1u"],
    },
    221: {  # Pm-3m
        "raman": ["T2g", "Eg"],
        "ir": ["T1u"],
        "acoustic": ["T1u"],
    },
    194: {  # P6₃/mmc
        "raman": ["E2g", "A1g", "E1g"],
        "ir": ["A2u (z)", "E1u (x,y)"],
        "acoustic": ["A2u", "E1u"],
    },
    186: {  # P6₃mc
        "raman": ["A1 (z)", "E1 (x,y)", "E2"],
        "ir": ["A1 (z)", "E1 (x,y)"],
        "acoustic": ["A1", "E1"],
    },
    123: {  # P4/mmm
        "raman": ["A1g", "B1g", "B2g", "Eg"],
        "ir": ["A2u (z)", "Eu (x,y)"],
        "acoustic": ["A2u", "Eu"],
    },
    166: {  # R-3m
        "raman": ["A1g", "Eg"],
        "ir": ["A2u (z)", "Eu (x,y)"],
        "acoustic": ["A2u", "Eu"],
    },
    11: {  # P2₁/m
        "raman": ["Ag", "Bg"],
        "ir": ["Au (z)", "Bu (x,y)"],
        "acoustic": ["Au", "Bu"],
    },
}


def parse_irreps_output(irreps_text: str) -> List[Dict]:
    """Parse phonopy `--irreps` output to extract mode symmetries.

    Args:
        irreps_text: Text output from `phonopy --irreps "0 0 0"`.

    Returns:
        List of dicts: {mode_number, frequency, irrep_label, irrep_type}.
    """
    modes = []
    lines = irreps_text.strip().split("\n")
    in_table = False

    for line in lines:
        line = line.strip()
        if "irreducible representation" in line.lower() or "irrep" in line.lower():
            in_table = True
            continue

        if in_table and line:
            # Try to parse a mode line
            # Format varies, typical: "mode #1: 5.123 THz  Ag"
            parts = line.split()
            if len(parts) < 3:
                continue

            try:
                mode_num = int(parts[0].strip("#:").replace("mode", "").strip())
            except (ValueError, IndexError):
                continue

            # Find frequency and irrep
            freq_idx = None
            for i, p in enumerate(parts):
                try:
                    float(p)
                    freq_idx = i
                    break
                except ValueError:
                    continue

            if freq_idx is not None:
                frequency = float(parts[freq_idx])
                irrep_label = " ".join(parts[freq_idx + 1:]) if freq_idx + 1 < len(parts) else ""
                modes.append({
                    "mode_number": mode_num,
                    "frequency_thz": frequency,
                    "frequency_cm1": frequency * THZ_TO_CM1,
                    "irrep_label": irrep_label,
                })

    return modes


def classify_raman_modes(
    modes: List[Dict],
    space_group: int,
) -> List[Dict]:
    """Classify Gamma-point modes by Raman/IR/acoustic activity.

    Args:
        modes: List of mode dicts (from parse_irreps_output).
        space_group: International space group number.

    Returns:
        Modes with added 'activity' field: 'raman', 'ir', 'acoustic', 'silent'.
    """
    sg_data = RAMAN_ACTIVE_IRREPS.get(space_group, {})
    raman_set = set(sg_data.get("raman", []))
    ir_set = set(sg_data.get("ir", []))
    acoustic_set = set(sg_data.get("acoustic", []))

    for mode in modes:
        irrep = mode["irrep_label"].strip()

        # Strip polarization markers (x), (y), (z)
        base_irrep = irrep.split("(")[0].strip()

        if base_irrep in acoustic_set:
            mode["activity"] = "acoustic"
        elif irrep in raman_set or base_irrep in raman_set:
            mode["activity"] = "raman"
        elif irrep in ir_set or base_irrep in ir_set:
            mode["activity"] = "ir"
        else:
            # Fuzzy match
            if any(r in irrep for r in ["g", "G"]):  # Gerade = Raman-active in centrosymmetric
                mode["activity"] = "raman"
            elif any(r in irrep for r in ["u", "U"]):  # Ungerade = IR-active in centrosymmetric
                mode["activity"] = "ir"
            else:
                mode["activity"] = "silent"

    return modes


def get_raman_active_modes(modes: List[Dict]) -> List[Dict]:
    """Filter only Raman-active modes.

    Args:
        modes: List of mode dicts with 'activity' field.

    Returns:
        Raman-active modes, sorted by frequency.
    """
    raman_modes = sorted(
        [m for m in modes if m.get("activity") == "raman"],
        key=lambda x: x["frequency_thz"],
    )
    return raman_modes


def format_mode_table(modes: List[Dict], activity_filter: Optional[str] = None) -> str:
    """Format mode information as a Markdown table.

    Args:
        modes: List of mode dicts.
        activity_filter: Filter by activity type ('raman', 'ir', etc.).

    Returns:
        Markdown table string.
    """
    if activity_filter:
        modes = [m for m in modes if m.get("activity") == activity_filter]

    lines = [
        "| # | Frequency (THz) | Frequency (cm⁻¹) | Irrep | Activity |",
        "|---|----------------:|-----------------:|-------|----------|",
    ]

    for m in modes:
        lines.append(
            f"| {m['mode_number']} | {m['frequency_thz']:.3f} | "
            f"{m['frequency_cm1']:.1f} | {m['irrep_label']} | "
            f"{m.get('activity', '-')} |"
        )

    return "\n".join(lines)
