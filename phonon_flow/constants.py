"""Physical constants and conversion factors for phonon calculations."""

# THz ↔ cm⁻¹ (wavenumber) conversion
# 1 THz = 33.3564095198152 cm⁻¹ (from c * 100 / (1e12))
THZ_TO_CM1 = 33.3564095198152
CM1_TO_THZ = 1.0 / THZ_TO_CM1

# THz ↔ meV (energy) conversion
# 1 THz = 4.135667662 meV (from Planck constant)
THZ_TO_MEV = 4.135667662
MEV_TO_THZ = 1.0 / THZ_TO_MEV

# cm⁻¹ ↔ meV
CM1_TO_MEV = THZ_TO_MEV / THZ_TO_CM1  # ~0.124
MEV_TO_CM1 = 1.0 / CM1_TO_MEV  # ~8.066

# Lattice vector notation for common high-symmetry paths
# Each entry: (label, coordinates_in_reciprocal)
HIGH_SYMMETRY_POINTS = {
    "Γ": (0.0, 0.0, 0.0),
    "X": (0.5, 0.0, 0.0),
    "M": (0.5, 0.5, 0.0),
    "R": (0.5, 0.5, 0.5),
    "S": (0.5, 0.5, 0.0),
    "Y": (0.0, 0.5, 0.0),
    "Z": (0.0, 0.0, 0.5),
    "U": (0.625, 0.25, 0.625),
    "T": (0.0, 0.5, 0.5),
    "K": (0.3333, 0.3333, 0.0),
    "H": (0.3333, 0.3333, 0.5),
    "A": (0.0, 0.0, 0.5),
    "L": (0.5, 0.0, 0.0),
}

# Predefined band paths for common Bravais lattices
# Format: list of (start_label, end_label, start_coords, end_coords)
BAND_PATHS = {
    "cubic_F": [
        ("Γ", "X", "0 0 0", "0 1/2 0"),
        ("X", "W", "0 1/2 0", "1/4 1/2 1/4"),
        ("W", "K", "1/4 1/2 1/4", "3/8 3/8 3/4"),
        ("K", "Γ", "3/8 3/8 3/4", "0 0 0"),
        ("Γ", "L", "0 0 0", "1/2 1/2 1/2"),
        ("L", "U", "1/2 1/2 1/2", "5/8 1/4 5/8"),
        ("U", "W", "5/8 1/4 5/8", "1/4 1/2 1/4"),
        ("W", "L", "1/4 1/2 1/4", "1/2 1/2 1/2"),
        ("L", "K", "1/2 1/2 1/2", "3/8 3/8 3/4"),
    ],
    "orthorhombic": [
        ("Γ", "X", "0 0 0", "1/2 0 0"),
        ("X", "S", "1/2 0 0", "1/2 1/2 0"),
        ("S", "Y", "1/2 1/2 0", "0 1/2 0"),
        ("Y", "Γ", "0 1/2 0", "0 0 0"),
        ("Γ", "Z", "0 0 0", "0 0 1/2"),
        ("Z", "U", "0 0 1/2", "1/2 0 1/2"),
        ("U", "R", "1/2 0 1/2", "1/2 1/2 1/2"),
        ("R", "T", "1/2 1/2 1/2", "0 1/2 1/2"),
        ("T", "Z", "0 1/2 1/2", "0 0 1/2"),
    ],
    "tetragonal_P": [
        ("Γ", "X", "0 0 0", "1/2 0 0"),
        ("X", "M", "1/2 0 0", "1/2 1/2 0"),
        ("M", "Γ", "1/2 1/2 0", "0 0 0"),
        ("Γ", "Z", "0 0 0", "0 0 1/2"),
        ("Z", "R", "0 0 1/2", "1/2 0 1/2"),
        ("R", "A", "1/2 0 1/2", "1/2 1/2 1/2"),
        ("A", "Z", "1/2 1/2 1/2", "0 0 1/2"),
    ],
    "hexagonal": [
        ("Γ", "M", "0 0 0", "1/2 0 0"),
        ("M", "K", "1/2 0 0", "1/3 1/3 0"),
        ("K", "Γ", "1/3 1/3 0", "0 0 0"),
        ("Γ", "A", "0 0 0", "0 0 1/2"),
        ("A", "L", "0 0 1/2", "1/2 0 1/2"),
        ("L", "H", "1/2 0 1/2", "1/3 1/3 1/2"),
        ("H", "A", "1/3 1/3 1/2", "0 0 1/2"),
    ],
    "monoclinic": [
        ("Γ", "Y", "0 0 0", "0 1/2 0"),
        ("Y", "H", "0 1/2 0", "0 1/2 1/2"),
        ("H", "C", "0 1/2 1/2", "0 0 1/2"),
        ("C", "E", "0 0 1/2", "1/2 0 1/2"),
        ("E", "M₁", "1/2 0 1/2", "1/2 1/2 1/2"),
        ("M₁", "A", "1/2 1/2 1/2", "1/2 1/2 0"),
        ("A", "X", "1/2 1/2 0", "0 0 0"),
        ("X", "H₁", "0 0 0", "0 1/2 1/2"),
    ],
    "Pnma": [
        ("Γ", "X", "0 0 0", "1/2 0 0"),
        ("X", "S", "1/2 0 0", "1/2 1/2 0"),
        ("S", "Y", "1/2 1/2 0", "0 1/2 0"),
        ("Y", "Γ", "0 1/2 0", "0 0 0"),
        ("Γ", "Z", "0 0 0", "0 0 1/2"),
        ("Z", "U", "0 0 1/2", "1/2 0 1/2"),
        ("U", "R", "1/2 0 1/2", "1/2 1/2 1/2"),
        ("R", "T", "1/2 1/2 1/2", "0 1/2 1/2"),
        ("T", "Z", "0 1/2 1/2", "0 0 1/2"),
    ],
}

# Default VASP parameters for different calculation types
DEFAULT_VASP_PARAMS = {
    "relax": {
        "ENCUT": 520,
        "EDIFF": 1e-5,
        "EDIFFG": -0.001,
        "NSW": 200,
        "IBRION": 2,
        "ISIF": 3,
        "ISMEAR": 1,
        "SIGMA": 0.2,
        "PREC": "Accurate",
        "LWAVE": False,
        "LCHARG": False,
    },
    "phonon_force": {
        "ENCUT": 520,
        "EDIFF": 1e-8,
        "NSW": 0,
        "IBRION": -1,
        "ISMEAR": 1,
        "SIGMA": 0.2,
        "PREC": "Accurate",
        "ADDGRID": True,
        "LWAVE": False,
        "LCHARG": False,
    },
    "scf": {
        "ENCUT": 520,
        "EDIFF": 1e-6,
        "NSW": 0,
        "IBRION": -1,
        "ISMEAR": -5,
        "PREC": "Accurate",
        "LWAVE": True,
        "LCHARG": True,
        "LORBIT": 11,
    },
}

# Supercell dimensions by crystal system
# (nx, ny, nz) tuples — ensure ~10 A in each direction
SUPERCELL_DIMENSIONS = {
    "cubic": (2, 2, 2),
    "tetragonal": (2, 2, 2),
    "orthorhombic": (2, 2, 2),
    "hexagonal": (3, 3, 2),
    "monoclinic": (2, 2, 2),
    "triclinic": (2, 2, 2),
    "trigonal": (2, 2, 2),
}
