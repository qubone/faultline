"""faultline: structured error handling and diagnostics for CLI toolchains.

Public API surface -- import everything you need directly from
``faultline``, e.g.::

    from faultline import UserError, error_catalog, recording, as_main
"""

from faultline.boundary import as_main, run_main
from faultline.diagnostics import BundleWriter, recording
from faultline.exceptions import (
    DataIntegrityError,
    InfrastructureError,
    InternalError,
    ToolchainError,
    UserError,
)
from faultline.registry import ErrorCatalog, ErrorSpec, error_catalog

__all__ = [
    "ToolchainError",
    "UserError",
    "InfrastructureError",
    "DataIntegrityError",
    "InternalError",
    "ErrorCatalog",
    "ErrorSpec",
    "error_catalog",
    "recording",
    "BundleWriter",
    "run_main",
    "as_main",
]

__version__ = "0.1.0"
