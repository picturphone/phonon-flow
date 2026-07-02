"""
PhononFlow test suite.

Currently tests are primarily integration tests that require
actual VASP + phonopy installation. Unit tests for config parsing
and template generation can run without VASP.
"""


def test_config_from_yaml():
    """Test loading config from YAML."""
    from phonon_flow.config import PhononConfig

    data = {
        "material": {
            "name": "Si",
            "potcar_elements": ["Si"],
            "crystal_system": "cubic",
            "space_group": 227,
        },
        "backend": {
            "type": "local",
        },
        "phonopy": {
            "supercell_dim": [2, 2, 2],
            "band_points": 101,
        },
        "output_dir": "./test_calc",
    }

    config = PhononConfig.from_dict(data)
    assert config.material.name == "Si"
    assert config.material.space_group == 227
    assert config.phonopy.supercell_dim == (2, 2, 2)


def test_incar_generation():
    """Test INCAR template generation."""
    from phonon_flow.phonon.templates import generate_incar_relax, generate_incar_phonon

    incar = generate_incar_relax(system="Test", encut=520)
    assert "SYSTEM = Test" in incar
    assert "ENCUT = 520" in incar
    assert "NSW = 200" in incar
    assert "IBRION = 2" in incar

    incar_ph = generate_incar_phonon(system="Test Phonon", encut=520)
    assert "NSW = 0" in incar_ph
    assert "IBRION = -1" in incar_ph
    assert "EDIFF = 1e-08" in incar_ph or "EDIFF = 1E-08" in incar_ph


def test_kpoints_generation():
    """Test KPOINTS generation."""
    from phonon_flow.phonon.templates import generate_kpoints

    kpts = generate_kpoints(grid=(8, 12, 8))
    assert "8 12 8" in kpts
    assert "Gamma" in kpts


def test_band_conf_generation():
    """Test band.conf generation."""
    from phonon_flow.phonon.templates import generate_band_conf

    conf = generate_band_conf(
        material_name="Si",
        dim=(2, 2, 2),
        band_points=101,
    )
    assert "ATOM_NAME = Si" in conf
    assert "DIM = 2 2 2" in conf
    assert "BAND_POINTS = 101" in conf


def test_constants():
    """Test unit conversion constants."""
    from phonon_flow.constants import THZ_TO_CM1, CM1_TO_THZ

    assert abs(THZ_TO_CM1 - 33.3564) < 0.01
    assert abs(THZ_TO_CM1 * CM1_TO_THZ - 1.0) < 1e-10


def test_raman_classification():
    """Test Raman mode classification."""
    from phonon_flow.phonon.raman import classify_raman_modes

    modes = [
        {"mode_number": 1, "frequency_thz": 0.0, "frequency_cm1": 0.0, "irrep_label": "B1u"},
        {"mode_number": 2, "frequency_thz": 5.65, "frequency_cm1": 188.5, "irrep_label": "B1g"},
        {"mode_number": 3, "frequency_thz": 6.80, "frequency_cm1": 226.8, "irrep_label": "Ag"},
    ]

    classified = classify_raman_modes(modes, space_group=62)
    assert classified[0]["activity"] == "acoustic"  # B1u is acoustic in Pnma
    assert classified[1]["activity"] == "raman"      # B1g is Raman
    assert classified[2]["activity"] == "raman"      # Ag is Raman
