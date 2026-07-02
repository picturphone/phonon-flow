"""Backend module exports."""

from phonon_flow.backends.base import RemoteBackend, SSHBackend, JobStatus
from phonon_flow.backends.hpc_slurm import HPCSLURMBackend
from phonon_flow.backends.local import LocalBackend


def create_backend(config) -> RemoteBackend:
    """Factory function to create the appropriate backend from config.

    Args:
        config: PhononConfig instance or BackendConfig instance.

    Returns:
        A RemoteBackend instance.
    """
    from phonon_flow.config import PhononConfig

    if isinstance(config, PhononConfig):
        backend_config = config.backend
    else:
        backend_config = config

    backend_type = backend_config.type

    if backend_type == "hpc_slurm":
        hpc = backend_config.hpc_slurm
        if hpc is None:
            raise ValueError("HPC SLURM config not provided")
        return HPCSLURMBackend(
            host=hpc.host,
            username=hpc.username,
            port=hpc.port,
            password=hpc.password,
            keyfile=hpc.keyfile,
            timeout=hpc.timeout,
            partition=hpc.partition,
            nodes=hpc.nodes,
            ntasks_per_node=hpc.ntasks_per_node,
            cpus_per_task=hpc.cpus_per_task,
            mem_per_cpu=hpc.mem_per_cpu,
            walltime=hpc.walltime,
            vasp_bin=hpc.vasp_bin,
            env_setup=hpc.env_setup,
            env_exports=hpc.env_exports,
            srun_cmd=hpc.srun_cmd,
            work_dir=hpc.work_dir,
        )

    elif backend_type == "local":
        return LocalBackend(work_dir=getattr(backend_config, "work_dir", "./calc"))

    else:
        raise ValueError(f"Unknown backend type: {backend_type}")


__all__ = [
    "RemoteBackend",
    "SSHBackend",
    "JobStatus",
    "HPCSLURMBackend",
    "LocalBackend",
    "create_backend",
]
