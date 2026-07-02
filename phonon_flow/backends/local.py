"""Local backend for testing and small calculations."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

from phonon_flow.backends.base import JobStatus, RemoteBackend


class LocalBackend(RemoteBackend):
    """Local machine backend for testing or direct execution.

    Useful for:
    - Phonopy post-processing (no remote needed)
    - Testing VASP inputs locally
    - Quick calculations on a workstation
    """

    def __init__(self, work_dir: str = "./calc"):
        self.work_dir = work_dir
        self._pids: dict = {}

    def connect(self) -> None:
        """No-op for local backend."""
        pass

    def disconnect(self) -> None:
        """No-op for local backend."""
        pass

    def run_command(self, cmd: str, timeout: int = 30) -> Tuple[str, str]:
        """Execute a local command."""
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.stderr

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Copy a file locally."""
        import shutil
        Path(remote_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, remote_path)

    def upload_content(self, content: str, remote_path: str) -> None:
        """Write content to a local file."""
        Path(remote_path).parent.mkdir(parents=True, exist_ok=True)
        with open(remote_path, "w", encoding="utf-8") as f:
            f.write(content)

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Copy a file locally."""
        import shutil
        shutil.copy2(remote_path, local_path)

    def file_exists(self, remote_path: str) -> bool:
        """Check if a local file exists."""
        return os.path.exists(remote_path)

    def mkdir(self, remote_path: str) -> None:
        """Create a local directory."""
        Path(remote_path).mkdir(parents=True, exist_ok=True)

    def submit_job(
        self, script_content: str, work_dir: str, script_name: str = "run.sh"
    ) -> str:
        """Run a local job."""
        self.mkdir(work_dir)
        script_path = os.path.join(work_dir, script_name)
        with open(script_path, "w") as f:
            f.write(script_content)

        proc = subprocess.Popen(
            ["bash", script_path],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        pid = str(proc.pid)
        self._pids[pid] = proc
        return f"local_{pid}"

    def check_job_status(self, job_id: str) -> JobStatus:
        """Check local job status."""
        pid = job_id.replace("local_", "")
        proc = self._pids.get(job_id)
        if proc is None:
            return JobStatus(job_id=job_id, state="UNKNOWN")

        poll = proc.poll()
        if poll is None:
            return JobStatus(job_id=job_id, state="RUNNING")
        elif poll == 0:
            return JobStatus(job_id=job_id, state="COMPLETED")
        else:
            return JobStatus(job_id=job_id, state="FAILED", exit_code=poll)

    def wait_for_job(
        self, job_id: str, poll_interval: int = 10, timeout: Optional[int] = None
    ) -> JobStatus:
        """Wait for local job completion."""
        start = time.time()
        while True:
            status = self.check_job_status(job_id)
            if status.state in ("COMPLETED", "FAILED"):
                return status
            if timeout and (time.time() - start) > timeout:
                return JobStatus(job_id=job_id, state="TIMEOUT")
            time.sleep(poll_interval)

    def cancel_job(self, job_id: str) -> None:
        """Kill a local job."""
        proc = self._pids.pop(job_id, None)
        if proc:
            proc.kill()
