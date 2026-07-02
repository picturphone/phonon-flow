#!/usr/bin/env python3
"""
Quick PhononFlow example — run a phonon calculation with HPC SLURM backend.

This script demonstrates the Python API for PhononFlow.
Prerequisites:
  - phonopy installed locally (post-processing)
  - VASP accessible on a HPC cluster via SSH + SLURM
  - A POSCAR file for your material

Usage:
  python quick_phonon.py
"""

from pathlib import Path
from phonon_flow import PhononConfig, PhononWorkflow
from phonon_flow.backends import HPCSLURMBackend

# ── Step 1: Configure ──────────────────────────────────

config = PhononConfig.from_dict({
    "material": {
        "name": "Si",
        "potcar_elements": ["Si"],
        "crystal_system": "cubic",
        "space_group": 227,
    },
    "backend": {"type": "hpc_slurm"},
    "phonopy": {"supercell_dim": [2, 2, 2], "band_points": 51},
    "output_dir": "./Si_phonon_calc",
})

# ── Step 2: Create POSCAR (Si diamond, 2 atoms) ────────
# Replace this with your own POSCAR!

poscar = """Si diamond
   1.0
     2.715  2.715  0.000
     2.715  0.000  2.715
     0.000  2.715  2.715
   Si
     2
Direct
  0.000  0.000  0.000
  0.250  0.250  0.250
"""

output_dir = Path(config.output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / "POSCAR").write_text(poscar)

# ── Step 3: Connect to HPC SLURM cluster ───────────────

backend = HPCSLURMBackend(
    host="login.hpc.example.com",
    port=22,
    username="YOUR_USERNAME",
    keyfile="~/.ssh/id_rsa",
    partition="YOUR_PARTITION",
    ntasks_per_node=32,
    vasp_bin="~/path/to/vasp_std",
    env_setup=[
        "module purge",
        "source ~/path/to/vasp/env.sh",
    ],
    env_exports={
        "I_MPI_PIN_DOMAIN": "numa",
        "OMP_NUM_THREADS": "1",
    },
    srun_cmd="srun --mpi=pmi2 vasp_std",
    work_dir="~/phonon_flow",
)

# ── Step 4: Run workflow ───────────────────────────────

wf = PhononWorkflow(config, backend=backend)
wf.run_all()  # Run full pipeline: relax → displace → forces → bands → Raman

print("\nDone! Results in:", config.output_dir)
