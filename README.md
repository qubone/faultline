# faultline

A structured error-handling and diagnostics framework for CLI toolchains and CI pipelines.

`faultline` exists to answer three questions automatically, for every failure in a
multi-package CLI toolchain: **whose fault is it, is it worth retrying, and what
evidence do we need to debug it** — without a human reading a stack trace to guess.

It was born out of maintaining Python packages feeding a CI pipeline used by
thousands of developers, where a mix of custom error codes, ad hoc exceptions,
and plain `logging` calls made support triage slow and debug data unreliable.

## Why not just use `structlog` / `tenacity` / `sentry-sdk`?

Those are great, and `faultline` is designed to sit alongside them, not replace
them. Each solves one slice of the problem (structured logging, retries, cloud
error reporting) — none of them unify **exception taxonomy → retry eligibility →
diagnostic capture → CI exit-code contract** into one coherent, self-documenting
system. That's the gap `faultline` fills.

## Core ideas

- **A small, opinionated exception taxonomy** (`UserError`, `InfrastructureError`,
  `DataIntegrityError`, `InternalError`) that every project's exceptions subclass.
  The category *is* the triage decision.
- **A registry/catalog** (`@error_catalog.register(...)`) that attaches a stable
  error code, retry eligibility, and remediation text to every exception class —
  one place, not scattered across the codebase.
- **A diagnostic "black box recorder"** (`recording()`) that keeps recent logs in
  memory and only writes a full diagnostic bundle to disk when something actually
  fails. Healthy runs stay quiet; failed runs get full forensics for free.
- **A process boundary handler** (`run_main` / `@as_main`) that turns exception
  categories into consistent exit codes and machine-readable CI summaries.

See [`docs/architecture.md`](docs/architecture.md) for how the pieces fit
together, and [`docs/ROADMAP.md`](docs/ROADMAP.md) for what's built vs. planned.

## Quickstart

This project uses [`uv`](https://docs.astral.sh/uv/) and targets Python 3.12+.

```bash
# Install dependencies (including dev tools)
uv sync --extra dev

# Run the test suite
uv run pytest

# Lint and type-check
uv run ruff check .
uv run mypy src

# Try the example CLI (it fails on purpose, to show the machinery)
uv run python examples/minimal_cli.py
```

## Minimal usage

```python
from faultline import UserError, error_catalog, as_main, recording

@error_catalog.register(
    code="MYPKG-001",
    remediation="Check that the config file exists and is valid YAML.",
)
class ConfigMissingError(UserError):
    """Raised when the tool can't find its config file."""

@as_main
def main() -> None:
    with recording() as correlation_id:
        # ... your real logic here ...
        raise ConfigMissingError("config.yml not found", context={"cwd": "."})

if __name__ == "__main__":
    main()
```

Running this prints a clear message + remediation to stderr and exits with
code `2` (the `UserError` exit code) — no ambiguity for Jenkins/Gradle about
whether this was a real bug or a bad invocation.

## Status

Early-stage / alpha. See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the milestone
plan. Not yet published to PyPI.

## License

MIT — see [`LICENSE`](LICENSE).
