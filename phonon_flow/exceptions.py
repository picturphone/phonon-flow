"""Exception classes for PhononFlow."""


class PhononFlowError(Exception):
    """Base exception for all PhononFlow errors."""


class BackendError(PhononFlowError):
    """Raised when a remote backend encounters an error."""


class SSHConnectionError(BackendError):
    """Raised when SSH connection fails."""


class SSHTimeoutError(BackendError):
    """Raised when SSH connection times out."""


class SSHAuthenticationError(BackendError):
    """Raised when SSH authentication fails."""


class SLURMError(BackendError):
    """Raised when SLURM job submission or monitoring fails."""


class HPCDeploymentError(BackendError):
    """Raised when VASP is not properly deployed on the HPC."""


class VASPError(PhononFlowError):
    """Raised when VASP calculation encounters an error."""


class VASPNotConvergedError(VASPError):
    """Raised when VASP calculation did not converge."""


class InputFileError(PhononFlowError):
    """Raised when required input files are missing or invalid."""


class POTCARError(InputFileError):
    """Raised when POTCAR generation fails."""


class PhonopyError(PhononFlowError):
    """Raised when phonopy operations fail."""


class KnowledgeBaseError(PhononFlowError):
    """Raised when knowledge base operations fail."""


class ConfigError(PhononFlowError):
    """Raised when configuration is invalid."""


class ValidationError(PhononFlowError):
    """Raised when validation step fails."""
