# PhononFlow

<p align="center">
  <b>First-Principles Phonon Calculation Workflow Engine for HPC Clusters</b><br>
  <em>Python Package · PyPI + GitHub</em>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#citation">Citation</a>
</p>

---

**PhononFlow** is a **Python library + CLI tool** (not an AI agent skill) that automates the entire DFT phonon calculation pipeline — from structure relaxation to publication-ready phonon dispersion and Raman activity analysis — with seamless remote execution on HPC clusters.

| Backend | Transport | Scheduler | Best For |
|---------|-----------|-----------|----------|
| **HPC Cluster** | SSH | SLURM | Production, large supercells |
| **Local** | None | None | Phonopy post-processing |

Results can be automatically archived to **Tencent IMA** knowledge base for team collaboration.

---

## Features

- **HPC remote execution** — Run VASP on SLURM clusters or locally via a unified API
- **End-to-end automation** — `relax → displace → forces → bands → Raman` in one command
- **Validation-first strategy** — Submit 1 test job, verify, then batch (saves compute-hours)
- **Raman activity classification** — Automatic Γ-point irreducible representation analysis
- **VESTA-compatible output** — Eigenvectors written for 3D vibration visualization
- **IMA knowledge base sync** — Archive results, configs, and reports to cloud knowledge base
- **Rich CLI** — Beautiful terminal UI with progress tracking
- **YAML-driven configuration** — Declarative, version-controllable, reproducible

## Quick Start

```bash
# 1. Install
pip install phonon-flow

# 2. Generate config (Si = standard VASP/Phonopy tutorial material)
phonon-flow init Si -e Si --crystal cubic --space-group 227 \
  --backend hpc_slurm -o si.yaml

# 3. Edit config (fill in paths, credentials)

# 4. Verify connectivity
phonon-flow check -c si.yaml

# 5. Run
phonon-flow run -c si.yaml
```

**Or via Python API:**

```python
from phonon_flow import PhononConfig, PhononWorkflow
from phonon_flow.backends import HPCSLURMBackend

config = PhononConfig.from_yaml("si_phonon.yaml")
backend = HPCSLURMBackend(
    host="login.hpc.example.com", port=22,
    username="YOUR_USERNAME", keyfile="~/.ssh/id_rsa",
    partition="YOUR_PARTITION", ntasks_per_node=32,
    vasp_bin="~/path/to/vasp_std",
    env_setup=["module purge", "source ~/path/to/vasp/env.sh"],
    env_exports={"I_MPI_PIN_DOMAIN": "numa"},
)

with PhononWorkflow(config, backend) as wf:
    wf.run_all()  # Full pipeline
```

## Installation

**External tools (install separately):**

| Tool | Required For | Installation |
|------|-------------|-------------|
| [VASP](https://www.vasp.at/) | DFT calculations (HPC cluster) | Licensed software — install on your HPC |
| [phonopy](https://phonopy.github.io/phonopy/) | Post-processing (local) | `conda install -c conda-forge phonopy` or `pip install phonopy` |

**Python dependencies (auto-installed):** Python ≥ 3.10, `paramiko`, `pyyaml`, `click`, `rich`

```bash
pip install phonon-flow

# For IMA knowledge base support:
pip install phonon-flow[knowledge]

# For development:
pip install phonon-flow[dev]
```

## Usage

### Command Line

```bash
# Initialize
phonon-flow init Si -e Si --crystal cubic --space-group 227
phonon-flow init MoS2 -e Mo,S --crystal hexagonal --space-group 194

# Verify
phonon-flow check -c si_phonon.yaml

# Run specific steps
phonon-flow run -c config.yaml -s relax -s displace

# Run all except sync
phonon-flow run -c config.yaml --skip sync

# Queue management (HPC only)
phonon-flow queue -c config.yaml        # List jobs
phonon-flow queue -c config.yaml --kill # Cancel all
```

### Python API

```python
from phonon_flow import PhononConfig, PhononWorkflow

# Load config
config = PhononConfig.from_yaml("config.yaml")

wf = PhononWorkflow(config)

# Run individual steps
results = wf.run_relax()      # Step 1
results = wf.run_displace()   # Step 2
results = wf.run_forces()     # Step 3
results = wf.run_bands()      # Step 4
results = wf.run_raman()      # Step 5

# Or the full pipeline
wf.run_all()

# Generate report
report = wf.render_report()
```

### Configuration

See `examples/si_phonon.yaml` for a complete annotated example.

```yaml
material:
  name: Si
  potcar_elements: [Si]
  crystal_system: cubic
  space_group: 227  # Fd-3m

backend:
  type: hpc_slurm
  hpc_slurm:
    host: login.hpc.example.com
    # ... credentials ...

phonopy:
  supercell_dim: [2, 2, 2]
  band_points: 101
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    CLI (click)                    │
│  phonon-flow {run, check, init, queue, status}   │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              PhononWorkflow                       │
│  ┌──────┐  ┌──────────┐  ┌──────┐  ┌─────────┐ │
│  │relax │→│ displace  │→│forces│→│  bands   │ │
│  └──────┘  └──────────┘  └──────┘  └────┬────┘ │
│                                         │        │
│  ┌─────────┐  ┌────────┐  ┌───────────┐│        │
│  │  sync   │← │ report │← │  raman    │◄        │
│  └────┬────┘  └────────┘  └───────────┘         │
└───────┼──────────────────────────────────────────┘
        │
┌───────▼────────┬──────────────────┬──────────────┐
│  IMA Client    │  Remote Backends │  Local Utils  │
│ (knowledge)    │  ┌─────────────┐ │  (phonopy)    │
│                │  │HPC SLURM    │ │               │
│ • create_note  │  │  (SSH)      │ │  • bands.py   │
│ • upload_file  │  ├─────────────┤ │  • raman.py   │
│ • search       │  │Local        │ │  • plotting   │
│ • sync_report  │  │  (direct)   │ │  • templates  │
│                │  └─────────────┘ │               │
└────────────────┴──────────────────┴───────────────┘
```

## Real-World Validation

PhononFlow has been validated on the standard VASP/Phonopy tutorial material **Si (diamond, Fd-3m, #227)**:

| Metric | Value |
|--------|-------|
| Supercell | 2×2×2 = 16 atoms |
| Displacements | 1 (high symmetry) |
| ENCUT | 520 eV |
| Total core-hours | ~1 (HPC, 32 cores/node) |
| Phonon modes | 6 (3 acoustic + 3 optical) |
| Stability | ✅ No imaginary frequencies |
| Raman-active | 1 mode (T₂g, ~520 cm⁻¹) |

> **Validator level**: Si is the official VASP tutorial system — anyone can reproduce the results.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

Areas we'd love help with:
- **New backends**: PBS/Torque, LSF, cloud (AWS Batch, GCP)
- **Support matrices**: DFT+U, HSE06, GW phonons
- **Visualization**: VESTA 3D rendering, interactive band plots
- **More space groups**: Raman classification tables
- **Testing**: Integration tests for various backends

## Citing

If you use PhononFlow in your research, please cite:

```bibtex
@software{phononflow2026,
  title = {PhononFlow: First-Principles Phonon Calculation Workflow Engine},
  author = {PhononFlow Contributors},
  year = {2026},
  url = {https://github.com/phonon-flow/phonon-flow},
}
```

This project builds on:
- [VASP](https://www.vasp.at/) — Vienna Ab initio Simulation Package
- [phonopy](https://phonopy.github.io/phonopy/) — Phonon calculation library
- [paramiko](https://www.paramiko.org/) — SSH library for Python

## License

MIT License. See [LICENSE](LICENSE) for details.
