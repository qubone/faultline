"""Top-level process boundary handler.

Every CLI entry point in a faultline-based tool should have exactly one
call to :func:`run_main` (or use the :func:`as_main` decorator) wrapping
its real logic. This is what turns exception categories into
consistent, predictable process exit codes -- so Gradle, Jenkins, or any
other orchestrator can branch on exit code instead of parsing log text
to guess what happened.
"""

from __future__ import annotations

import functools
import json
import logging
import sys
from collections.abc import Callable
from pathlib import Path

from faultline.exceptions import ToolchainError

logger = logging.getLogger("faultline.boundary")


def run_main[R](
    func: Callable[[], R],
    *,
    ci_summary_path: Path | None = None,
) -> R:
    """Run ``func``, translating any ``ToolchainError`` into a clean exit.

    On UserError / DataIntegrityError / InfrastructureError / InternalError,
    prints the message and remediation to stderr, optionally writes a
    small JSON summary for CI systems to read, and exits with the
    error's ``exit_code``. Unrecognized exceptions are logged with a
    full traceback and treated as an internal failure (exit code 1),
    since faultline can't know their category.

    Args:
        func: A zero-argument callable containing your program's real
            logic (typically your existing ``main()``).
        ci_summary_path: If given, a JSON file describing the failure
            (or success) is written here for CI systems to consume
            without needing to parse stdout/stderr.
    """
    try:
        return func()
    except ToolchainError as exc:
        _emit(exc, ci_summary_path)
        sys.exit(exc.exit_code)
    except Exception as exc:  # noqa: BLE001 - last line of defense
        logger.critical("Unhandled exception", exc_info=True)
        _emit(exc, ci_summary_path, unexpected=True)
        sys.exit(1)


def _emit(exc: BaseException, ci_summary_path: Path | None, *, unexpected: bool = False) -> None:
    if isinstance(exc, ToolchainError):
        print(f"\n\u274c {type(exc).__name__}: {exc.message}", file=sys.stderr)
        if exc.remediation:
            print(f"   \u2192 {exc.remediation}", file=sys.stderr)
        payload = exc.to_dict()
    else:
        print(f"\n\u274c Unexpected error: {exc}", file=sys.stderr)
        payload = {
            "error_class": type(exc).__name__,
            "message": str(exc),
            "unexpected": unexpected,
        }

    if ci_summary_path is not None:
        ci_summary_path.parent.mkdir(parents=True, exist_ok=True)
        ci_summary_path.write_text(json.dumps(payload, indent=2, default=str))


def as_main[R](func: Callable[[], R]) -> Callable[[], R | None]:
    """Decorator form of :func:`run_main` for simple ``def main(): ...`` entry points."""

    @functools.wraps(func)
    def wrapper() -> R | None:
        return run_main(func)

    return wrapper
