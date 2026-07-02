"""VASP input file template generators.

All templates generate standard VASP input files (INCAR, KPOINTS, POSCAR, POTCAR)
with sensible defaults tuned for phonon calculations.
"""

from __future__ import annotations

from typing import Dict, List, Optional


def generate_incar_relax(
    system: str = "Structure Relaxation",
    encut: int = 520,
    ediff: float = 1e-5,
    ediffg: float = -0.001,
    nsw: int = 200,
    ibrion: int = 2,
    isif: int = 3,
    ismear: int = 1,
    sigma: float = 0.2,
    prec: str = "Accurate",
    lwave: bool = False,
    lcharg: bool = False,
    ispin: Optional[int] = None,
    magmom: Optional[List[float]] = None,
    ivdw: Optional[int] = None,
    lda_plus_u: bool = False,
    lda_uu: Optional[List[float]] = None,
    lda_ul: Optional[List[int]] = None,
    extra: Optional[Dict] = None,
) -> str:
    """Generate INCAR for structure relaxation.

    Args:
        system: System description (max 40 chars).
        encut: Plane-wave energy cutoff (eV).
        ediff: Electronic convergence criterion.
        ediffg: Ionic convergence (negative = force criterion).
        nsw: Maximum ionic steps.
        ibrion: Algorithm (2 = CG, 1 = quasi-Newton).
        isif: Degrees of freedom (3 = full relaxation).
        ismear: Smearing method (1 = Methfessel-Paxton, 0 = Gaussian, -5 = tetrahedron).
        sigma: Smearing width (eV).
        prec: Precision level.
        lwave: Write WAVECAR.
        lcharg: Write CHGCAR.
        ispin: Spin polarization (2 = collinear).
        magmom: Initial magnetic moments per atom.
        ivdw: Van der Waals correction method.
        lda_plus_u: Enable DFT+U.
        lda_uu: U values per species.
        lda_ul: L quantum numbers per species.
        extra: Additional INCAR tags.

    Returns:
        INCAR file content.
    """
    lines = [f"SYSTEM = {system[:40]}"]
    lines.append("! === Basic Parameters ===")
    lines.append(f"ENCUT = {encut}")
    lines.append(f"EDIFF = {ediff:.0e}")
    lines.append(f"EDIFFG = {ediffg:.4f}")
    lines.append(f"NSW = {nsw}")
    lines.append(f"IBRION = {ibrion}")
    lines.append(f"ISIF = {isif}")

    lines.append("! === Electronic Structure ===")
    lines.append(f"ISMEAR = {ismear}")
    lines.append(f"SIGMA = {sigma:.2f}")

    if ispin:
        lines.append("! === Magnetic Configuration ===")
        lines.append(f"ISPIN = {ispin}")
        if magmom:
            mag_str = " ".join(str(m) for m in magmom)
            lines.append(f"MAGMOM = {mag_str}")

    if lda_plus_u and lda_uu:
        lines.append("! === DFT+U ===")
        lines.append("LDAU = .TRUE.")
        lines.append("LDAUTYPE = 2")
        uu_str = " ".join(str(u) for u in lda_uu)
        lines.append(f"LDAUU = {uu_str}")
        if lda_ul:
            ul_str = " ".join(str(l) for l in lda_ul)
            lines.append(f"LDAUL = {ul_str}")

    if ivdw:
        lines.append(f"! === Dispersion Correction ===")
        lines.append(f"IVDW = {ivdw}")

    lines.append("! === Precision ===")
    lines.append(f"PREC = {prec}")
    lines.append("! === File Output ===")
    lines.append(f"LWAVE = {'.TRUE.' if lwave else '.FALSE.'}")
    lines.append(f"LCHARG = {'.TRUE.' if lcharg else '.FALSE.'}")

    if extra:
        lines.append("! === Custom Tags ===")
        for key, val in extra.items():
            if isinstance(val, bool):
                val_str = ".TRUE." if val else ".FALSE."
            else:
                val_str = str(val)
            lines.append(f"{key} = {val_str}")

    return "\n".join(lines) + "\n"


def generate_incar_phonon(
    system: str = "Phonon Force Calculation",
    encut: int = 520,
    ediff: float = 1e-8,
    ismear: int = 1,
    sigma: float = 0.2,
    prec: str = "Accurate",
    addgrid: bool = True,
    ispin: Optional[int] = None,
    magmom: Optional[List[float]] = None,
    lda_plus_u: bool = False,
    lda_uu: Optional[List[float]] = None,
    lda_ul: Optional[List[int]] = None,
    extra: Optional[Dict] = None,
) -> str:
    """Generate INCAR for phonon force constant calculation.

    Key differences from relax INCAR:
    - NSW = 0, IBRION = -1 (fixed atoms, Hellmann-Feynman forces only)
    - EDIFF = 1e-8 (higher electronic precision for accurate forces)
    - ADDGRID = .TRUE. (improved real-space grid)
    - LWAVE/LCHARG = .FALSE. (not needed for phonon)

    Args:
        system: System description.
        encut: Energy cutoff (must match relax).
        ediff: Electronic convergence (stricter than relax).
        ismear: Smearing method.
        sigma: Smearing width.
        prec: Precision level.
        addgrid: Enable additional support grid.
        ispin: Spin polarization.
        magmom: Magnetic moments (must match relax).
        lda_plus_u: Enable DFT+U (must match relax).
        lda_uu: U values.
        lda_ul: L quantum numbers.
        extra: Additional INCAR tags.

    Returns:
        INCAR file content.
    """
    lines = [f"SYSTEM = {system[:40]}"]
    lines.append("! === Basic Parameters ===")
    lines.append(f"ENCUT = {encut}")
    lines.append(f"EDIFF = {ediff:.0e}")
    lines.append(f"NSW = 0")
    lines.append(f"IBRION = -1")

    lines.append("! === Electronic Structure ===")
    lines.append(f"ISMEAR = {ismear}")
    lines.append(f"SIGMA = {sigma:.2f}")

    if ispin:
        lines.append("! === Magnetic Configuration ===")
        lines.append(f"ISPIN = {ispin}")
        if magmom:
            mag_str = " ".join(str(m) for m in magmom)
            lines.append(f"MAGMOM = {mag_str}")

    if lda_plus_u and lda_uu:
        lines.append("! === DFT+U ===")
        lines.append("LDAU = .TRUE.")
        lines.append("LDAUTYPE = 2")
        uu_str = " ".join(str(u) for u in lda_uu)
        lines.append(f"LDAUU = {uu_str}")
        if lda_ul:
            ul_str = " ".join(str(l) for l in lda_ul)
            lines.append(f"LDAUL = {ul_str}")

    lines.append("! === Precision ===")
    lines.append(f"PREC = {prec}")
    lines.append(f"ADDGRID = {'.TRUE.' if addgrid else '.FALSE.'}")

    lines.append("! === File Output ===")
    lines.append("LWAVE = .FALSE.")
    lines.append("LCHARG = .FALSE.")

    if extra:
        lines.append("! === Custom Tags ===")
        for key, val in extra.items():
            if isinstance(val, bool):
                val_str = ".TRUE." if val else ".FALSE."
            else:
                val_str = str(val)
            lines.append(f"{key} = {val_str}")

    return "\n".join(lines) + "\n"


def generate_kpoints(
    method: str = "Gamma",
    grid: tuple = (8, 8, 8),
    comment: str = "Automatic mesh",
) -> str:
    """Generate KPOINTS file.

    Args:
        method: k-point method ("Gamma", "Monkhorst", or "automatic").
        grid: (nx, ny, nz) k-point mesh.
        comment: Header comment.

    Returns:
        KPOINTS file content.
    """
    lines = [comment, "0", method, f" {grid[0]} {grid[1]} {grid[2]}", "0 0 0"]
    return "\n".join(lines) + "\n"


def generate_band_conf(
    material_name: str = "",
    dim: tuple = (2, 2, 2),
    band_path: Optional[List] = None,
    band_points: int = 101,
    primitive_axis: Optional[tuple] = None,
) -> str:
    """Generate phonopy band.conf for band structure calculation.

    Args:
        material_name: Material name (atom labels).
        dim: Supercell dimensions.
        band_path: List of (start_label, end_label, start, end) tuples,
                   or list of high-symmetry point labels.
        band_points: Number of points along each segment.
        primitive_axis: Primitive axis transform (for non-primitive cells).

    Returns:
        band.conf content.
    """
    lines = []
    if material_name:
        lines.append(f"ATOM_NAME = {material_name}")
    lines.append(f"DIM = {dim[0]} {dim[1]} {dim[2]}")

    if band_path:
        if isinstance(band_path[0], tuple) and len(band_path[0]) == 4:
            # Full path: (start_label, end_label, start, end)
            band_str = "  ".join(
                f"{s}  {e}" for _, _, s, e in band_path
            )
            label_str = " ".join(f"{s} {e}" for s, e, _, _ in band_path)
        else:
            # Simple label list
            band_str = "  ".join(band_path)
            label_str = " ".join(band_path)

        lines.append(f"BAND = {band_str}")
        if len(label_str) < 100:
            lines.append(f"BAND_LABELS = {label_str}")

    lines.append(f"BAND_POINTS = {band_points}")

    if primitive_axis:
        pa = primitive_axis
        lines.append(f"PRIMITIVE_AXIS = {pa[0]} {pa[1]} {pa[2]}")

    lines.append("")  # Trailing newline
    return "\n".join(lines)


def generate_potcar(elements: List[str], potcar_sources: List[str]) -> str:
    """Concatenate individual POTCAR files into a single POTCAR.

    IMPORTANT: Elements must be in the SAME ORDER as in POSCAR!

    Args:
        elements: List of element symbols (in POSCAR order).
        potcar_sources: List of POTCAR file contents (or paths).

    Returns:
        Concatenated POTCAR content.
    """
    parts = []
    for elem, source in zip(elements, potcar_sources):
        if source.startswith("/") or source.startswith("~"):
            # Assume it's a file path
            with open(source, "r") as f:
                parts.append(f.read())
        else:
            parts.append(source)
        if elem not in parts[-1][:100]:
            print(f"Warning: Element {elem} may not match POTCAR content")

    return "".join(parts)
