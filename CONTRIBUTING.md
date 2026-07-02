# Contributing to PhononFlow

Thank you for your interest in contributing! PhononFlow is a community-driven project and we welcome contributions of all kinds.

## Development Setup

```bash
# Clone
git clone https://github.com/phonon-flow/phonon-flow.git
cd phonon-flow

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install in development mode with dev dependencies
pip install -e ".[dev, docs]"

# Run tests
pytest phonon_flow/tests/ -v

# Code quality
black phonon_flow/
ruff check phonon_flow/
mypy phonon_flow/
```

## Project Structure

```
phonon-flow/
├── phonon_flow/          # Main package
│   ├── backends/          # Remote computation backends
│   │   ├── base.py        # Abstract SSH backend
│   │   ├── raspberry_pi.py # Raspberry Pi (no scheduler)
│   │   ├── hpc_slurm.py   # HPC cluster (SLURM)
│   │   └── local.py       # Local execution
│   ├── phonon/            # Phonon calculation logic
│   │   ├── workflow.py    # Core workflow orchestrator
│   │   ├── bands.py       # Band structure analysis
│   │   ├── raman.py       # Raman activity classification
│   │   └── templates/     # VASP input generators
│   ├── knowledge/         # IMA knowledge base integration
│   │   └── ima_client.py  # IMA API wrapper
│   ├── utils/             # Plotting & utilities
│   ├── cli.py             # Command-line interface
│   ├── config.py          # YAML config system
│   └── constants.py       # Physical constants
├── examples/              # Example configs & scripts
├── docs/                  # Documentation
└── tests/                 # Test suite
```

## Adding a New Backend

1. Subclass `RemoteBackend` (or `SSHBackend`)
2. Implement all abstract methods
3. Register in `phonon_flow/backends/__init__.py`
4. Add config in `phonon_flow/config.py`
5. Add tests

## Adding Raman Tables for New Space Groups

Edit `phonon_flow/phonon/raman.py` → `RAMAN_ACTIVE_IRREPS` dictionary.

## Pull Request Process

1. Fork the repo and create a branch
2. Add tests for new functionality
3. Run `black . && ruff check .`
4. Submit PR with a clear description

## Questions?

Open an issue or start a discussion!
