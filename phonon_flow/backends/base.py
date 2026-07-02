"""Backend abstraction for remote VASP execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import paramiko


@dataclass
class JobStatus:
    """Status of a submitted job."""
    job_id: str
    state: str  # QUEUED, RUNNING, COMPLETED, FAILED
    name: str = ""
    elapsed: str = ""
    exit_code: Optional[int] = None
    output: str = ""


class RemoteBackend(ABC):
    """Abstract base class for all remote computation backends."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the remote backend."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection."""
        ...

    @abstractmethod
    def run_command(self, cmd: str, timeout: int = 30) -> Tuple[str, str]:
        """Execute a command on the backend.

        Returns:
            Tuple of (stdout, stderr).
        """
        ...

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file to the backend."""
        ...

    @abstractmethod
    def upload_content(self, content: str, remote_path: str) -> None:
        """Upload string content as a file."""
        ...

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file from the backend."""
        ...

    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists."""
        ...

    @abstractmethod
    def mkdir(self, remote_path: str) -> None:
        """Create a directory (recursively)."""
        ...

    @abstractmethod
    def submit_job(self, script_content: str, work_dir: str, script_name: str = "submit.slurm") -> str:
        """Submit a job and return the job ID."""
        ...

    @abstractmethod
    def check_job_status(self, job_id: str) -> JobStatus:
        """Check the status of a submitted job."""
        ...

    @abstractmethod
    def wait_for_job(self, job_id: str, poll_interval: int = 60, timeout: Optional[int] = None) -> JobStatus:
        """Wait for a job to complete."""
        ...

    @abstractmethod
    def cancel_job(self, job_id: str) -> None:
        """Cancel a running or queued job."""
        ...


class SSHBackend(RemoteBackend):
    """SSH-based remote backend.

    Base implementation for backends that use SSH (Raspberry Pi, HPC).
    """

    def __init__(
        self,
        host: str,
        username: str,
        port: int = 22,
        password: Optional[str] = None,
        keyfile: Optional[str] = None,
        timeout: int = 15,
    ):
        self.host = host
        self.username = username
        self.port = port
        self.password = password
        self.keyfile = keyfile
        self.timeout = timeout
        self._ssh: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def connect(self) -> None:
        """Establish SSH connection."""
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
            "timeout": self.timeout,
        }

        if self.keyfile:
            key = paramiko.RSAKey.from_private_key_file(self.keyfile)
            connect_kwargs["pkey"] = key
        elif self.password:
            connect_kwargs["password"] = self.password

        self._ssh.connect(**connect_kwargs)
        self._sftp = self._ssh.open_sftp()

    def disconnect(self) -> None:
        """Close the SSH connection."""
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._ssh:
            self._ssh.close()
            self._ssh = None

    def run_command(self, cmd: str, timeout: int = 30) -> Tuple[str, str]:
        """Execute a remote command."""
        if not self._ssh:
            raise RuntimeError("Not connected. Call connect() first.")
        stdin, stdout, stderr = self._ssh.exec_command(cmd, timeout=timeout)
        stdout.channel.recv_exit_status()
        return stdout.read().decode("utf-8", errors="replace"), stderr.read().decode("utf-8", errors="replace")

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a local file to the remote host."""
        if not self._sftp:
            raise RuntimeError("Not connected. Call connect() first.")
        self._sftp.put(local_path, remote_path)

    def upload_content(self, content: str, remote_path: str) -> None:
        """Write string content directly to a remote file."""
        if not self._sftp:
            raise RuntimeError("Not connected. Call connect() first.")
        with self._sftp.open(remote_path, "w") as f:
            f.write(content)

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a remote file to the local machine."""
        if not self._sftp:
            raise RuntimeError("Not connected. Call connect() first.")
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        self._sftp.get(remote_path, local_path)

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on the remote."""
        try:
            if not self._sftp:
                return False
            self._sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def mkdir(self, remote_path: str) -> None:
        """Create remote directory recursively."""
        self.run_command(f"mkdir -p {remote_path}")
