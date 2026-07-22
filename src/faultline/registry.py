"""Central registry mapping exception classes to catalog metadata.

Every user-facing exception class should be decorated with
``@error_catalog.register(...)``. This is the single source of truth
that powers retry-policy decisions, exit-code lookups, and the
auto-generated error catalog docs (see :mod:`faultline.catalog`, coming
in a later milestone).

Keeping this metadata attached to the class itself -- rather than
configured separately in a retry decorator, a docs page, and a support
runbook -- is what prevents those three things from drifting out of
sync with each other.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from faultline.exceptions import ToolchainError

ExcT = TypeVar("ExcT", bound=type[ToolchainError])


@dataclass(frozen=True)
class ErrorSpec:
    """Metadata attached to a registered exception class."""

    code: str
    category: str
    retryable: bool
    remediation: str
    description: str = ""


class ErrorCatalog:
    """Holds all registered exception classes and their metadata.

    Typical usage::

        error_catalog = ErrorCatalog()

        @error_catalog.register(
            code="WRAPGEN-014",
            remediation="Check that the input schema matches the template version.",
        )
        class SchemaMismatchError(DataIntegrityError):
            '''Raised when a wrapper template's schema version doesn't match the input.'''

    Large multi-package setups (like a three-package monorepo) can either
    share one process-wide catalog (see ``faultline.registry.error_catalog``
    below) or instantiate one ``ErrorCatalog`` per package and merge their
    ``all_specs()`` output when generating combined documentation.
    """

    def __init__(self) -> None:
        self._by_class: dict[type[ToolchainError], ErrorSpec] = {}
        self._by_code: dict[str, type[ToolchainError]] = {}

    def register(
        self,
        *,
        code: str,
        retryable: bool | None = None,
        remediation: str = "",
        description: str = "",
    ) -> Callable[[ExcT], ExcT]:
        """Class decorator that registers a ToolchainError subclass.

        Args:
            code: A stable, unique identifier (e.g. ``"WRAPGEN-014"``).
                Convention: ``<PACKAGE>-<NNN>``. Never reuse or renumber
                a retired code -- treat these like public API.
            retryable: Overrides the category default (e.g. mark a
                specific InfrastructureError subclass as not retryable
                because retrying it is known to be unsafe). Defaults to
                the base category's ``retryable`` value.
            remediation: Human-readable fix-it text shown to end users
                and included in the generated error catalog.
            description: Longer explanation for the catalog docs.
                Defaults to the exception class's docstring.
        """

        def decorator(exc_cls: ExcT) -> ExcT:
            if code in self._by_code:
                existing = self._by_code[code]
                raise ValueError(
                    f"Error code {code!r} is already registered to "
                    f"{existing.__module__}.{existing.__qualname__}"
                )
            if not (isinstance(exc_cls, type) and issubclass(exc_cls, ToolchainError)):
                raise TypeError(
                    f"{exc_cls!r} must subclass faultline.ToolchainError "
                    "(UserError, InfrastructureError, DataIntegrityError, or InternalError)"
                )

            resolved_retryable = exc_cls.retryable if retryable is None else retryable
            spec = ErrorSpec(
                code=code,
                category=exc_cls.__mro__[1].__name__,  # nearest base category
                retryable=resolved_retryable,
                remediation=remediation,
                description=description or (exc_cls.__doc__ or "").strip(),
            )
            exc_cls.retryable = resolved_retryable  # type: ignore[assignment]
            # Give raised instances access to the registered code/remediation
            # automatically, so callers don't have to repeat remediation text
            # at every raise site -- that duplication is exactly the kind of
            # drift this library exists to eliminate.
            exc_cls.code = code  # type: ignore[assignment]
            exc_cls._default_remediation = remediation  # type: ignore[attr-defined]
            self._by_class[exc_cls] = spec
            self._by_code[code] = exc_cls
            return exc_cls

        return decorator

    def spec_for(self, exc: ToolchainError | type[ToolchainError]) -> ErrorSpec | None:
        """Look up the registered metadata for an exception instance or class."""
        exc_cls = exc if isinstance(exc, type) else type(exc)
        return self._by_class.get(exc_cls)

    def class_for_code(self, code: str) -> type[ToolchainError] | None:
        """Reverse lookup: find the exception class for a given error code."""
        return self._by_code.get(code)

    def all_specs(self) -> list[ErrorSpec]:
        """Return every registered spec, sorted by error code."""
        return sorted(self._by_class.values(), key=lambda s: s.code)


#: Default, process-wide catalog. Most single-package projects can just
#: import and use this directly. Import it as
#: ``from faultline.registry import error_catalog``.
error_catalog = ErrorCatalog()
