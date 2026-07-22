"""Minimal example showing faultline wired into a CLI entry point.

Run it with:

    uv run python examples/minimal_cli.py

It will fail on purpose (the input file doesn't exist) so you can see:
  - the clean stderr message + remediation text
  - the process exit code (2, for UserError)
  - a diagnostic bundle written under ./diagnostic-bundles/
"""

from __future__ import annotations

import logging
import pathlib

from faultline import (
    DataIntegrityError,
    UserError,
    as_main,
    error_catalog,
    recording,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("example")


@error_catalog.register(
    code="EXAMPLE-001",
    remediation="Make sure the input file exists and is readable.",
)
class InputFileMissingError(UserError):
    """Raised when the input file the CLI was pointed at doesn't exist."""


@error_catalog.register(
    code="EXAMPLE-002",
    remediation="Validate the XML against the expected schema before rerunning.",
)
class InvalidXmlError(DataIntegrityError):
    """Raised when the input XML can't be parsed."""


def process(path: str) -> None:
    p = pathlib.Path(path)
    if not p.exists():
        raise InputFileMissingError(f"Input file not found: {path}", context={"path": path})

    if p.read_text().strip() == "":
        raise InvalidXmlError(f"Input file is empty: {path}", context={"path": path})

    logger.info("Processed %s successfully", path)


@as_main
def main() -> None:
    with recording(logger=logger) as correlation_id:
        logger.info("Starting run %s", correlation_id)
        process("does-not-exist.xml")


if __name__ == "__main__":
    main()
