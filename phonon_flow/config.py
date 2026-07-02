"""Configuration system for PhononFlow.

Supports YAML-based configuration files for defining:
- Remote backends (HPC SLURM cluster)
- Material system parameters
- VASP calculation settings
- Phonopy workflow parameters
- Knowledge base integration (IMA)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


@dataclass
class SSHBackendConfig:
    """SSH connection configuration for a remote backend."""
    host: str
    username: str
    port: int = 22
    password: Optional[str] = None
    keyfile: Optional[str] = None
    timeout: int = 15


@dataclass
class HPCSLURMConfig(SSHBackendConfig):
    """HPC SLURM cluster backend configuration.

    Example:
        hpc_slurm:
          host: login.hpc.example.com
          port: 22
          username: your_username
          keyfile: ~/.ssh/id_rsa_hpc
          partition: YOUR_PARTITION
          nodes: 1
          ntasks_per_node: 32
          vasp_bin: ~/path/to/vasp_std
          env_setup:
            - "module purge"
            - "source ~/path/to/vasp/env.sh"
          env_exports:
            I_MPI_PIN_DOMAIN: numa
            OMP_NUM_THREADS: 1
          srun_cmd: "srun --mpi=pmi2 vasp_std"
          work_dir: ~/wsy
    """

    partition: str = "default"
    nodes: int = 1
    ntasks_per_node: int = 32
    cpus_per_task: int = 1
    mem_per_cpu: str = "2gb"
    walltime: str = "12:00:00"

    vasp_bin: str = ""
    env_setup: List[str] = field(default_factory=list)
    env_exports: Dict[str, str] = field(default_factory=dict)
    srun_cmd: str = "srun --mpi=pmi2 vasp_std"
    work_dir: str = "~"


@dataclass
class MagneticConfig:
    """Magnetic configuration for spin-polarized calculations."""
    enabled: bool = False
    magmom: List[float] = field(default_factory=list)
    lda_plus_u: bool = False
    lda_uu: List[float] = field(default_factory=list)
    ldaa_uj: List[float] = field(default_factory=list)
    lda_ul: List[int] = field(default_factory=list)


@dataclass
class VASPSettings:
    """VASP calculation parameters for a specific step."""
    encut: int = 520
    ediff: float = 1e-5
    ediffg: float = -0.001
    nsw: int = 200
    ibrion: int = 2
    isif: int = 3
    ismear: int = 1
    sigma: float = 0.2
    prec: str = "Accurate"
    addgrid: bool = False
    lwave: bool = False
    lcharg: bool = False
    lorbit: Optional[int] = None
    ivdw: Optional[int] = None
    algo: Optional[str] = None
    lreal: Optional[str] = None
    isym: Optional[int] = None
    nelm: Optional[int] = None
    kspacing: Optional[float] = None


@dataclass
class KPointsConfig:
    """K-point mesh configuration."""
    method: str = "automatic"  # automatic, gamma, monkhorst
    grid: tuple = (8, 8, 8)
    shift: tuple = (0, 0, 0)


@dataclass
class PhonopyConfig:
    """Phonopy calculation parameters."""
    supercell_dim: tuple = (2, 2, 2)
    band_path: List[tuple] = field(default_factory=list)
    band_points: int = 101
    tolerance: float = 1e-5
    q_mesh: tuple = (0, 0, 0)  # (0,0,0) = only Gamma


@dataclass
class IMAKnowledgeConfig:
    """IMA knowledge base integration configuration."""
    enabled: bool = False
    client_id: str = ""
    api_key: str = ""
    knowledge_base_id: str = ""
    auto_sync: bool = False
    sync_results: bool = True
    sync_inputs: bool = True
    sync_report: bool = True


@dataclass
class MaterialConfig:
    """Material system definition."""
    name: str = ""
    poscar_path: str = ""
    potcar_elements: List[str] = field(default_factory=list)
    potcar_dir: Optional[str] = None
    magnetic: Optional[MagneticConfig] = None
    crystal_system: str = ""  # cubic, orthorhombic, hexagonal, etc.
    space_group: Optional[int] = None


@dataclass
class BackendConfig:
    """Unified backend configuration."""
    type: str = "hpc_slurm"  # hpc_slurm, local
    hpc_slurm: Optional[HPCSLURMConfig] = None


@dataclass
class PhononConfig:
    """Complete PhononFlow configuration.

    Can be instantiated from a YAML file or programmatically.
    """

    material: MaterialConfig = field(default_factory=MaterialConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)

    # Per-step VASP settings (override defaults)
    relax_settings: VASPSettings = field(default_factory=VASPSettings)
    phonon_settings: VASPSettings = field(default_factory=lambda: VASPSettings(
        ediff=1e-8, nsw=0, ibrion=-1, addgrid=True
    ))

    # K-point configurations
    relax_kpoints: KPointsConfig = field(default_factory=lambda: KPointsConfig(grid=(8, 12, 8)))
    phonon_kpoints: KPointsConfig = field(default_factory=lambda: KPointsConfig(grid=(6, 6, 6)))

    # Phonopy settings
    phonopy: PhonopyConfig = field(default_factory=PhonopyConfig)

    # IMA knowledge base
    knowledge: Optional[IMAKnowledgeConfig] = None

    # Global settings
    output_dir: str = "./phonon_calc"
    save_intermediate: bool = True
    verbose: bool = False

    def to_yaml(self, path: Union[str, Path]) -> None:
        """Export configuration to YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        d = {}
        d["material"] = _dataclass_to_dict(self.material)
        d["backend"] = _dataclass_to_dict(self.backend)
        d["relax_settings"] = _dataclass_to_dict(self.relax_settings)
        d["phonon_settings"] = _dataclass_to_dict(self.phonon_settings)
        d["relax_kpoints"] = _dataclass_to_dict(self.relax_kpoints)
        d["phonon_kpoints"] = _dataclass_to_dict(self.phonon_kpoints)
        d["phonopy"] = _dataclass_to_dict(self.phonopy)
        if self.knowledge:
            d["knowledge"] = _dataclass_to_dict(self.knowledge)
        d["output_dir"] = self.output_dir
        d["save_intermediate"] = self.save_intermediate
        d["verbose"] = self.verbose
        return _strip_none(d)

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "PhononConfig":
        """Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file.

        Returns:
            PhononConfig instance.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhononConfig":
        """Create configuration from dictionary."""
        config = cls()

        if "material" in data:
            config.material = _dict_to_material(data["material"])

        if "backend" in data:
            config.backend = _dict_to_backend(data["backend"])

        if "relax_settings" in data:
            config.relax_settings = VASPSettings(**_strip_none_dict(data["relax_settings"]))

        if "phonon_settings" in data:
            config.phonon_settings = VASPSettings(**_strip_none_dict(data["phonon_settings"]))

        if "relax_kpoints" in data:
            config.relax_kpoints = KPointsConfig(**data["relax_kpoints"])

        if "phonon_kpoints" in data:
            config.phonon_kpoints = KPointsConfig(**data["phonon_kpoints"])

        if "phonopy" in data:
            pd = data["phonopy"]
            supercell = pd.get("supercell_dim", (2, 2, 2))
            if isinstance(supercell, list):
                supercell = tuple(supercell)
            config.phonopy = PhonopyConfig(
                supercell_dim=supercell,
                band_path=pd.get("band_path", []),
                band_points=pd.get("band_points", 101),
                tolerance=pd.get("tolerance", 1e-5),
                q_mesh=pd.get("q_mesh", (0, 0, 0)),
            )

        if "knowledge" in data:
            config.knowledge = IMAKnowledgeConfig(**data["knowledge"])

        if "output_dir" in data:
            config.output_dir = data["output_dir"]
        if "save_intermediate" in data:
            config.save_intermediate = data["save_intermediate"]
        if "verbose" in data:
            config.verbose = data["verbose"]

        return config


# Helper functions for config serialization

def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    """Convert a dataclass to a dictionary, excluding None values."""
    if obj is None:
        return {}
    result = {}
    for key, value in obj.__dict__.items():
        if value is not None:
            if isinstance(value, tuple):
                value = list(value)
            elif hasattr(value, "__dataclass_fields__"):
                value = _dataclass_to_dict(value)
            elif isinstance(value, list) and value and hasattr(value[0], "__dataclass_fields__"):
                value = [_dataclass_to_dict(v) for v in value]
            result[key] = value
    return result


def _strip_none(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from a dictionary recursively."""
    return {k: v for k, v in d.items() if v is not None and v != []}


def _strip_none_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove None values from a flat dictionary."""
    return {k: v for k, v in d.items() if v is not None}


def _dict_to_material(d: Dict[str, Any]) -> MaterialConfig:
    """Create MaterialConfig from dictionary."""
    mag = None
    if "magnetic" in d and d["magnetic"]:
        mag_kwargs = d["magnetic"].copy()
        mag = MagneticConfig(**mag_kwargs)

    return MaterialConfig(
        name=d.get("name", ""),
        poscar_path=d.get("poscar_path", ""),
        potcar_elements=d.get("potcar_elements", []),
        potcar_dir=d.get("potcar_dir"),
        magnetic=mag,
        crystal_system=d.get("crystal_system", ""),
        space_group=d.get("space_group"),
    )


def _dict_to_backend(d: Dict[str, Any]) -> BackendConfig:
    """Create BackendConfig from dictionary."""
    bc = BackendConfig(type=d.get("type", "hpc_slurm"))

    if d.get("hpc_slurm"):
        bc.hpc_slurm = HPCSLURMConfig(**d["hpc_slurm"])

    return bc
