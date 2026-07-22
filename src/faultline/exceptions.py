"""Core exception taxonomy for faultline.

Every error in a faultline-based tool should subclass one of the four
base categories below. The category answers three questions at a glance:

- Who needs to act? (the user, the infrastructure, upstream data, or the
  maintainers of this tool)
- Is it worth retrying?
- What process exit code should this produce?

Projects should not raise these base classes directly in application
code -- subclass them and register the subclass via
``@error_catalog.register(...)`` in :mod:`faultline.registry`.
"""

from __future__ import annotations

from typing import Any


class ToolchainError(Exception):
    """Base class for every error raised through faultline.

    Attributes:
        message: Human-readable summary of what went wrong.
        context: Structured, machine-readable data about the failure
            (file paths, line numbers, request IDs, etc). This is what
            gets written into diagnostic bundles and structured logs --
            keep it JSON-serializable.
        remediation: A short, human-readable suggestion for how to fix
            or work around the problem. Shown directly to end users.
    """

    #: Default process exit code for this category. Individual exception
    #: classes may override this on the class itself if needed.
    exit_code: int = 1

    #: Whether errors of this category are, in general, worth retrying.
    #: Concrete exception classes should set this via the registry
    #: rather than overriding it directly, so it stays in sync with the
    #: error catalog metadata.
    retryable: bool = False

    #: Stable error code, set automatically by `@error_catalog.register(...)`.
    #: ``None`` for classes that haven't been registered yet.
    code: str | None = None

    #: Remediation text set automatically by `@error_catalog.register(...)`.
    #: Used as a fallback when a raise site doesn't pass its own
    #: `remediation=` -- see `__init__` below. Not meant to be set directly.
    _default_remediation: str | None = None

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        remediation: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = context or {}
        # Prefer remediation given explicitly at the raise site (it may
        # have call-specific detail); fall back to whatever was registered
        # for this class via @error_catalog.register(...), so remediation
        # text only has to be written once per error class, not once per
        # raise site.
        self.remediation = remediation if remediation is not None else self._default_remediation

    def to_dict(self) -> dict[str, Any]:
        """Serialize this error for logs, CI summaries, and diagnostic bundles."""
        return {
            "error_class": type(self).__name__,
            "code": self.code,
            "message": self.message,
            "context": self.context,
            "remediation": self.remediation,
            "exit_code": self.exit_code,
            "retryable": self.retryable,
        }

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.message


class UserError(ToolchainError):
    """The caller did something the tool can't proceed with.

    Bad config, missing files, invalid CLI arguments. This is *not* a bug
    in the toolchain -- it should never generate a support ticket on its
    own. It should produce a clear, actionable message and exit quietly.
    """

    exit_code = 2


class InfrastructureError(ToolchainError):
    """Caused by the environment, not the code or the input.

    Network blips, REST API timeouts, disk-full, DNS failures, flaky CI
    runners. Usually transient and often worth an automatic retry.
    """

    exit_code = 3
    retryable = True


class DataIntegrityError(ToolchainError):
    """The input data itself is malformed or inconsistent.

    Corrupt XML, schema mismatches, unexpected encodings. Distinct from
    UserError because the *data* is broken, not necessarily how the tool
    was invoked -- often the data originated from an upstream system the
    caller doesn't control.
    """

    exit_code = 4


class InternalError(ToolchainError):
    """A genuine bug in the toolchain itself.

    If this is raised, some assumption in faultline-based code was wrong.
    Always worth a real investigation -- never silently retried, never
    presented to the end user as something they can fix.
    """

    exit_code = 5
