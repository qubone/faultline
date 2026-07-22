"""Command-line entry point for faultline itself (not for consumers' tools).

Currently a placeholder. Milestone 7 (Auto-Generated Error Catalog) will
add a real ``faultline catalog build`` subcommand that imports a
project's registered error classes and renders ``docs/error-catalog.md``.
"""

from __future__ import annotations

import sys


def app() -> None:
    print("faultline CLI: no subcommands implemented yet (see ROADMAP.md, Milestone 7).")
    sys.exit(0)


if __name__ == "__main__":
    app()
