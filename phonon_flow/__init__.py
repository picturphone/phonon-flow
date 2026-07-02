"""
PhononFlow — Remote first-principles phonon calculation workflow engine for HPC clusters.

PhononFlow automates the entire DFT phonon calculation pipeline:
from structure relaxation to phonon dispersion plotting and Raman activity analysis,
with seamless remote execution on SLURM-based HPC clusters.

Core capabilities:
- HPC SLURM remote execution (SSH + SLURM job management, local)
- End-to-end phonon workflow (relax → displace → force → bands → Raman)
- VESTA-compatible eigenvector visualization
- IMA knowledge base integration for result archival
- Smart job submission with validation-first strategy
"""

__version__ = "0.1.0"
__author__ = "PhononFlow Contributors"
__license__ = "MIT"

from phonon_flow.config import PhononConfig
from phonon_flow.phonon.workflow import PhononWorkflow

__all__ = ["PhononConfig", "PhononWorkflow", "__version__"]
