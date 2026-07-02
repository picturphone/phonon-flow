"""HPC SLURM backend for large-scale VASP calculations on clusters."""

from __future__ import annotations

import re
import time
from typing import List, Optional, Tuple

from phonon_flow.backends.base import JobStatus, SSHBackend
from phonon_flow.exceptions import (
    HPCDeploymentError,
    SLURMError,
)


class HPCSLURMBackend(SSHBackend):
    """HPC cluster backend with SLURM job scheduler.

    Provides full job lifecycle management:
    - SLURM script generation & submission
    - Job monitoring & queue management
    - Environment setup validation
    - VASP deployment verification

    Key design decisions:
    - Each displaced configuration gets its own SLURM script (validated approach)
    - Validation-first strategy: submit 1 test job, verify, then batch
    """

    def __init__(
        self,
        host: str,
        username: str,
        port: int = 22,
        password: Optional[str] = None,
        keyfile: Optional[str] = None,
        timeout: int = 15,
        partition: str = "default",
        nodes: int = 1,
        ntasks_per_node: int = 32,
        cpus_per_task: int = 1,
        mem_per_cpu: str = "2gb",
        walltime: str = "12:00:00",
        vasp_bin: str = "",
        env_setup: Optional[List[str]] = None,
        env_exports: Optional[dict] = None,
        srun_cmd: str = "srun --mpi=pmi2 vasp_std",
        work_dir: str = "~",
    ):
        super().__init__(
            host=host,
            username=username,
            port=port,
            password=password,
            keyfile=keyfile,
            timeout=timeout,
        )
        self.partition = partition
        self.nodes = nodes
        self.ntasks_per_node = ntasks_per_node
        self.cpus_per_task = cpus_per_task
        self.mem_per_cpu = mem_per_cpu
        self.walltime = walltime
        self.vasp_bin = vasp_bin
        self.env_setup = env_setup or []
        self.env_exports = env_exports or {}
        self.srun_cmd = srun_cmd
        self.work_dir = work_dir

    def expand_work_dir(self, subdir: str) -> str:
        """Get the absolute path for a work subdirectory."""
        out, _ = self.run_command(f"echo {self.work_dir}/{subdir}")
        return out.strip()

    def submit_job(
        self,
        script_content: str,
        work_dir: str,
        script_name: str = "submit.slurm",
    ) -> str:
        """Submit a SLURM job.

        Args:
            script_content: SLURM script content.
            work_dir: Remote working directory.
            script_name: Name of the script file.

        Returns:
            SLURM job ID (as string).

        Raises:
            SLURMError: If submission fails.
        """
        self.mkdir(work_dir)
        script_path = f"{work_dir}/{script_name}"
        self.upload_content(script_content, script_path)

        out, err = self.run_command(f"cd {work_dir} && sbatch {script_name}")
        if err and "error" in err.lower():
            raise SLURMError(f"Job submission failed: {err}")

        # Parse job ID from "Submitted batch job 12345"
        match = re.search(r"(\d+)", out)
        if not match:
            raise SLURMError(f"Could not parse job ID from: {out}")

        return match.group(1)

    def check_job_status(self, job_id: str) -> JobStatus:
        """Check the status of a SLURM job.

        Uses squeue for queued/running, sacct for completed jobs.
        """
        # Try squeue first
        out, _ = self.run_command(
            f'squeue -j {job_id} --noheader --format="%i %T %j %M" 2>/dev/null || echo ""'
        )

        if out.strip():
            parts = out.strip().split()
            if len(parts) >= 2:
                state = parts[1]
                state_map = {
                    "PD": "QUEUED",
                    "R": "RUNNING",
                    "CG": "COMPLETING",
                    "CF": "CONFIGURING",
                }
                return JobStatus(
                    job_id=job_id,
                    state=state_map.get(state, state),
                    name=parts[2] if len(parts) > 2 else "",
                    elapsed=parts[3] if len(parts) > 3 else "",
                )

        # Try sacct for completed/failed jobs
        out, _ = self.run_command(
            f'sacct -j {job_id} --noheader --format="JobID,State,ExitCode" --parsable2 2>/dev/null'
        )

        for line in out.strip().split("\n"):
            if "batch" in line or "extern" in line:
                continue
            parts = line.split("|")
            if len(parts) >= 2:
                state = parts[1]
                exit_code = parts[2].split(":")[0] if len(parts) > 2 else ""
                state_map = {
                    "COMPLETED": "COMPLETED",
                    "FAILED": "FAILED",
                    "TIMEOUT": "FAILED",
                    "CANCELLED": "FAILED",
                    "NODE_FAIL": "FAILED",
                }
                return JobStatus(
                    job_id=job_id,
                    state=state_map.get(state, state),
                    exit_code=int(exit_code) if exit_code.isdigit() else None,
                )

        return JobStatus(job_id=job_id, state="UNKNOWN")

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: int = 60,
        timeout: Optional[int] = None,
    ) -> JobStatus:
        """Wait for a SLURM job to complete, polling periodically.

        Args:
            job_id: SLURM job ID.
            poll_interval: Seconds between status checks.
            timeout: Maximum wait time in seconds. None = no limit.

        Returns:
            Final JobStatus.
        """
        start = time.time()
        while True:
            status = self.check_job_status(job_id)
            if status.state in ("COMPLETED", "FAILED"):
                return status
            if timeout and (time.time() - start) > timeout:
                return JobStatus(job_id=job_id, state="TIMEOUT", name=status.name)
            time.sleep(poll_interval)

    def cancel_job(self, job_id: str) -> None:
        """Cancel a SLURM job."""
        self.run_command(f"scancel {job_id}")

    def list_queue(self) -> str:
        """List all jobs in the queue for the current user."""
        out, _ = self.run_command(f'squeue -u {self.username} --format="%.10i %.8j %.2t %.10M"')
        return out

    def delete_queue_all(self) -> None:
        """Cancel all jobs for the current user."""
        out, _ = self.run_command(f"squeue -u {self.username} --noheader --format='%i' | xargs -r scancel")
        print(f"Canceled jobs: {out.strip()}")

    def verify_environment(self) -> bool:
        """Verify that VASP can be loaded and executed.

        Runs a check to confirm the VASP binary is accessible
        after the environment setup commands.

        Returns:
            True if VASP is properly deployed.
        """
        check_script = ""
        for cmd in self.env_setup:
            check_script += f"{cmd}\n"
        check_script += f"which {self.vasp_bin.split('/')[-1]} 2>/dev/null || "
        check_script += f"test -f {self.vasp_bin} && echo 'VASP_OK' || echo 'VASP_NOT_FOUND'"

        out, _ = self.run_command(check_script)
        return "VASP_OK" in out

    def generate_slurm_script(
        self,
        job_name: str,
        work_dir: str,
        extra_sbatch: Optional[dict] = None,
    ) -> str:
        """Generate a standard SLURM submission script.

        Args:
            job_name: SLURM job name (max 8 chars recommended).
            work_dir: Working directory for the calculation.
            extra_sbatch: Additional SBATCH directives.

        Returns:
            SLURM script content.
        """
        lines = [
            "#!/bin/bash",
            f"#SBATCH -J {job_name[:8]}",
            f"#SBATCH -N {self.nodes}",
            f"#SBATCH --ntasks-per-node={self.ntasks_per_node}",
            f"#SBATCH --cpus-per-task={self.cpus_per_task}",
            f"#SBATCH --mem-per-cpu={self.mem_per_cpu}",
            f"#SBATCH -p {self.partition}",
            f"#SBATCH --output=%x_%j.out",
            f"#SBATCH --error=%x_%j.err",
            f"#SBATCH --time={self.walltime}",
        ]

        if extra_sbatch:
            for key, val in extra_sbatch.items():
                lines.append(f"#SBATCH {key}={val}")

        lines.append(f"")
        lines.append(f"cd {work_dir}")
        lines.append(f"")

        # Environment setup
        lines.append("# === Environment Setup ===")
        for cmd in self.env_setup:
            lines.append(cmd)
        for key, val in self.env_exports.items():
            lines.append(f"export {key}={val}")
        lines.append(f"")

        # Job info
        lines.extend([
            'echo "Job: $SLURM_JOB_NAME"',
            'echo "Node: $(hostname)"',
            'echo "Cores: $SLURM_NTASKS"',
            'echo "Start: $(date)"',
            "",
        ])

        # Run VASP
        lines.extend([
            self.srun_cmd,
            "",
        ])

        # Completion
        lines.extend([
            'echo "End: $(date)"',
        ])

        return "\n".join(lines)

    def generate_phonon_slurm_script(
        self,
        disp_id: str,
        work_dir: str,
        material_name: str = "",
    ) -> str:
        """Generate a SLURM script specifically for phonon force calculations.

        Args:
            disp_id: Displacement ID (e.g., "001").
            work_dir: Working directory for the calculation.
            material_name: Material name for job naming.

        Returns:
            SLURM script content.
        """
        name = f"{material_name[:4]}_ph{disp_id}" if material_name else f"ph{disp_id}"
        return self.generate_slurm_script(job_name=name, work_dir=work_dir)
