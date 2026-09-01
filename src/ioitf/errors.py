"""Stable error classes and specification exit codes."""

EXIT_MATCH = 0
EXIT_MISMATCH = 1
EXIT_SPECIFICATION = 2
EXIT_UNSUPPORTED = 3
EXIT_RUNNER = 4
EXIT_REFERENCE = 5


class IOITFError(Exception):
    exit_code = EXIT_SPECIFICATION


class ValidationError(IOITFError):
    """Schema, canonicalization, hash, or input-contract failure."""


class UnsupportedError(IOITFError):
    exit_code = EXIT_UNSUPPORTED


class RunnerError(IOITFError):
    exit_code = EXIT_RUNNER


class ReferenceOracleError(IOITFError):
    exit_code = EXIT_REFERENCE

