"""Phonon plotting utilities."""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import yaml


def plot_phonon_bands(
    band_yaml_path: str,
    output: str = "phonon_band.png",
    title: str = "Phonon Dispersion",
    dpi: int = 300,
    figsize: tuple = (8, 6),
    line_color: str = "#2196F3",
    line_width: float = 1.2,
    show_grid: bool = False,
    y_unit: str = "THz",
    save: bool = True,
) -> plt.Figure:
    """Plot phonon band structure from band.yaml.

    Args:
        band_yaml_path: Path to band.yaml file.
        output: Output image path.
        title: Plot title.
        dpi: Image resolution.
        figsize: Figure size in inches.
        line_color: Band line color.
        line_width: Band line width.
        show_grid: Show grid lines.
        y_unit: Frequency unit ('THz' or 'cm⁻¹').
        save: Save to file if True.

    Returns:
        Matplotlib Figure.
    """
    from phonon_flow.constants import THZ_TO_CM1

    # Load data
    with open(band_yaml_path, "r") as f:
        data = yaml.safe_load(f)

    nqpoints = data["nqpoint"]
    nbands = len(data["phonon"][0]["band"])

    freqs = np.zeros((nbands, nqpoints))
    dists = np.zeros(nqpoints)

    for i, q in enumerate(data["phonon"]):
        for j, band in enumerate(q["band"]):
            freqs[j, i] = band["frequency"]
        dists[i] = q["distance"]

    if y_unit == "cm⁻¹":
        freqs *= THZ_TO_CM1

    # Plot
    fig, ax = plt.subplots(figsize=figsize)

    for band in freqs:
        ax.plot(dists, band, color=line_color, linewidth=line_width, alpha=0.8)

    # Zero line
    ax.axhline(0, color="red", linewidth=0.5, linestyle="--", alpha=0.5)

    # High-symmetry points
    labels = data.get("labels", [])
    if labels:
        tick_positions = [l[1] for l in labels]
        tick_labels = []
        for l in labels:
            name = l[0]
            if "\\Gamma" in name or "GAMMA" in name.upper():
                name = "Γ"
            tick_labels.append(f"${name}$")

        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, fontsize=12)

        for pos in tick_positions:
            ax.axvline(pos, color="gray", linewidth=0.5, linestyle="--", alpha=0.3)

    # Styling
    ax.set_xlabel("Wave Vector", fontsize=13)
    ylabel = f"Frequency ({y_unit})"
    ax.set_ylabel(ylabel, fontsize=13)
    ax.set_title(title, fontsize=14, fontweight="bold")

    if y_unit == "THz":
        ax.set_ylim(-0.5, freqs.max() * 1.08)

    if show_grid:
        ax.grid(True, alpha=0.3)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    if save:
        plt.savefig(output, dpi=dpi, bbox_inches="tight")
        print(f"Plot saved to: {output}")

    return fig


def plot_phonon_dos(
    dos_dat_path: str = "total_dos.dat",
    output: str = "phonon_dos.png",
    title: str = "Phonon Density of States",
    dpi: int = 300,
    figsize: tuple = (6, 5),
    fill: bool = True,
    fill_color: str = "#2196F3",
    fill_alpha: float = 0.3,
    line_color: str = "#2196F3",
    line_width: float = 1.5,
) -> plt.Figure:
    """Plot phonon density of states from total_dos.dat.

    Args:
        dos_dat_path: Path to total_dos.dat (phonopy output).
        output: Output image path.
        title: Plot title.
        dpi: Image resolution.
        figsize: Figure size.
        fill: Fill under curve.
        fill_color: Fill color.
        fill_alpha: Fill transparency.
        line_color: Line color.
        line_width: Line width.

    Returns:
        Matplotlib Figure.
    """
    data = np.loadtxt(dos_dat_path)
    freq = data[:, 0]  # THz
    dos = data[:, 1]

    fig, ax = plt.subplots(figsize=figsize)

    if fill:
        ax.fill_between(freq, dos, alpha=fill_alpha, color=fill_color)

    ax.plot(freq, dos, color=line_color, linewidth=line_width)

    ax.set_xlabel("Frequency (THz)", fontsize=13)
    ax.set_ylabel("DOS (states/THz)", fontsize=13)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlim(0, freq.max() * 1.05)
    ax.set_ylim(0, dos.max() * 1.1)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=dpi, bbox_inches="tight")

    return fig
