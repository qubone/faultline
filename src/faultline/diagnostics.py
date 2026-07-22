"""Diagnostic 'black box recorder' for faultline.

Keeps a bounded, in-memory ring buffer of recent log records. On a
normal run, nothing is ever written to disk -- the buffer just gets
overwritten as it fills. The moment an exception escapes the
``recording()`` context manager, the buffer plus contextual metadata is
flushed to a timestamped bundle directory, so the failure is debuggable
without needing to reproduce it -- this is what directly targets
"test failures without debug data" style support tickets.
"""

from __future__ import annotations

import json
import logging
import platform
import sys
import time
import traceback
import uuid
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from faultline.exceptions import ToolchainError


class _RingBufferHandler(logging.Handler):
    """A ``logging.Handler`` that keeps only the last N formatted records."""

    def __init__(self, capacity: int = 500) -> None:
        super().__init__()
        self.buffer: deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(self.format(record))
        except Exception:  # noqa: BLE001 - logging must never crash the run
            pass


@dataclass
class BundleWriter:
    """Writes diagnostic bundles to disk when a run fails.

    Attributes:
        output_dir: Directory bundles are written under. Each failed run
            gets its own timestamped subdirectory. Point this at a path
            your CI system archives as a build artifact.
    """

    output_dir: Path = field(default_factory=lambda: Path("./diagnostic-bundles"))

    def write(
        self,
        *,
        exc: BaseException,
        log_lines: list[str],
        correlation_id: str,
        extra_context: dict[str, Any] | None = None,
    ) -> Path:
        bundle_dir = self.output_dir / f"{int(time.time())}-{correlation_id}"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        error_payload: dict[str, Any]
        if isinstance(exc, ToolchainError):
            error_payload = exc.to_dict()
        else:
            error_payload = {"error_class": type(exc).__name__, "message": str(exc)}
        error_payload["traceback"] = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )

        manifest = {
            "correlation_id": correlation_id,
            "timestamp": time.time(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "error": error_payload,
            "extra_context": extra_context or {},
        }

        (bundle_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
        (bundle_dir / "recent.log").write_text("\n".join(log_lines))

        return bundle_dir


@contextmanager
def recording(
    *,
    logger: logging.Logger | None = None,
    capacity: int = 500,
    bundle_writer: BundleWriter | None = None,
    correlation_id: str | None = None,
    extra_context: dict[str, Any] | None = None,
) -> Iterator[str]:
    """Record logs in memory; flush a diagnostic bundle only on failure.

    Yields the correlation ID for this run, so callers can thread it
    into downstream subprocess calls, REST request headers, or Jenkins
    build parameters for later correlation.

    Example::

        with recording(logger=logging.getLogger("wrapper_gen")) as cid:
            run_pipeline_stage()
    """
    target_logger = logger or logging.getLogger()
    handler = _RingBufferHandler(capacity=capacity)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    target_logger.addHandler(handler)

    # A handler's own level only filters what *it* processes -- it does
    # nothing if the logger's own effective level already discards the
    # record first. Since the whole point of `recording()` is to capture
    # debug-level detail even when normal output is quieter, temporarily
    # widen the logger's own level for the duration of the block and
    # restore it afterwards.
    previous_level = target_logger.level
    if target_logger.getEffectiveLevel() > logging.DEBUG:
        target_logger.setLevel(logging.DEBUG)

    cid = correlation_id or str(uuid.uuid4())

    try:
        yield cid
    except BaseException as exc:  # noqa: BLE001 - intentionally broad; we re-raise below
        writer = bundle_writer or BundleWriter()
        bundle_path = writer.write(
            exc=exc,
            log_lines=list(handler.buffer),
            correlation_id=cid,
            extra_context=extra_context,
        )
        target_logger.error("Diagnostic bundle written to %s", bundle_path)
        raise
    finally:
        target_logger.removeHandler(handler)
        target_logger.setLevel(previous_level)
