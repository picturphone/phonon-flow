"""Phonon dispersion and band structure analysis."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import yaml

from phonon_flow.constants import THZ_TO_CM1


def load_band_yaml(band_yaml_path: str) -> dict:
    """Load a phonopy band.yaml file.

    Args:
        band_yaml_path: Path to band.yaml.

    Returns:
        Parsed band data dictionary.
    """
    with open(band_yaml_path, "r") as f:
        return yaml.safe_load(f)


def extract_frequencies(band_data: dict) -> Tuple[np.ndarray, np.ndarray]:
    """Extract frequency bands and q-point distances from band.yaml data.

    Args:
        band_data: Parsed band.yaml data.

    Returns:
        Tuple of (frequencies, q_distances):
            - frequencies: (nbands, nqpoints) array in THz
            - q_distances: (nqpoints,) array of cumulative distances
    """
    nqpoints = band_data["nqpoint"]
    nbands = len(band_data["phonon"][0]["band"])

    frequencies = np.zeros((nbands, nqpoints))
    q_distances = np.zeros(nqpoints)

    for i, q in enumerate(band_data["phonon"]):
        for j, band in enumerate(q["band"]):
            frequencies[j, i] = band["frequency"]
        q_distances[i] = q["distance"]

    return frequencies, q_distances


def check_stability(
    band_data: dict,
    tolerance: float = -0.5,
) -> Tuple[bool, float, str]:
    """Check dynamical stability from phonon frequencies.

    Args:
        band_data: Parsed band.yaml data.
        tolerance: Threshold for "soft" tolerance (in THz).

    Returns:
        Tuple of (is_stable, min_frequency, verdict_string).
    """
    min_freq = float("inf")
    for q in band_data["phonon"]:
        for band in q["band"]:
            min_freq = min(min_freq, band["frequency"])

    if min_freq >= 0:
        return True, min_freq, f"Stable (min = {min_freq:.4f} THz = {min_freq * THZ_TO_CM1:.1f} cm⁻¹)"
    elif min_freq > tolerance:
        return True, min_freq, f"Marginally stable (min = {min_freq:.4f} THz, within tolerance)"
    else:
        return False, min_freq, f"Unstable (min = {min_freq:.4f} THz, soft modes detected)"


def get_band_structure_summary(band_data: dict) -> dict:
    """Generate a summary of the phonon band structure.

    Args:
        band_data: Parsed band.yaml data.

    Returns:
        Dictionary with summary statistics.
    """
    frequencies, q_distances = extract_frequencies(band_data)
    is_stable, min_freq, verdict = check_stability(band_data)

    return {
        "nbands": frequencies.shape[0],
        "nqpoints": frequencies.shape[1],
        "is_dynamically_stable": is_stable,
        "min_frequency_thz": float(min_freq),
        "min_frequency_cm1": float(min_freq * THZ_TO_CM1),
        "max_frequency_thz": float(np.max(frequencies)),
        "max_frequency_cm1": float(np.max(frequencies) * THZ_TO_CM1),
        "frequency_range_thz": (
            float(np.min(frequencies[frequencies > 0])) if np.any(frequencies > 0) else 0.0,
            float(np.max(frequencies)),
        ),
        "num_acoustic_modes": 3,
        "num_optical_modes": frequencies.shape[0] - 3,
        "gamma_point_frequencies_thz": frequencies[:, 0].tolist(),
        "verdict": verdict,
    }


def extract_gamma_eigenvectors(band_data: dict) -> list:
    """Extract eigenvectors at the Gamma point (q-index 0).

    Args:
        band_data: Parsed band.yaml data.

    Returns:
        List of dicts with {band_index, frequency, eigenvectors} for each mode.
    """
    q = band_data["phonon"][0]
    modes = []
    for b_idx, band in enumerate(q["band"]):
        modes.append({
            "band_index": b_idx + 1,
            "frequency": band["frequency"],
            "eigenvector": band.get("eigenvector", []),
        })
    return modes
