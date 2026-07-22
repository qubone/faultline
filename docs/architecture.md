# Architecture

## Module map

```
faultline/
├── exceptions.py    Base taxonomy: ToolchainError → UserError / InfrastructureError /
│                     DataIntegrityError / InternalError. No dependencies on
│                     anything else in the package — this is the foundation
│                     everything else builds on.
│
├── registry.py       ErrorCatalog + the @error_catalog.register(...) decorator.
│                     Attaches a stable code, retry eligibility, and remediation
│                     text to each concrete exception class. Depends only on
│                     exceptions.py.
│
├── diagnostics.py     recording() context manager + BundleWriter. Keeps a ring
│                      buffer of recent logs in memory; flushes a diagnostic
│                      bundle to disk only when an exception escapes. Depends
│                      only on exceptions.py (for ToolchainError.to_dict()).
│
├── boundary.py         run_main() / @as_main. The single top-level handler each
│                       CLI entry point calls. Converts exceptions into exit
│                       codes and an optional CI-readable JSON summary. Depends
│                       only on exceptions.py.
│
├── retry.py            (Milestone 6, not yet built) Declarative retry policy
│                        that reads `retryable` from the registry instead of
│                        being configured separately.
│
├── catalog.py           (Milestone 7, not yet built) Renders all registered
│                         ErrorSpecs into a Markdown/HTML error catalog.
│
└── cli.py                `faultline` command-line entry point (currently a
                           placeholder; will host `faultline catalog build`).
```

## Data flow for a single failing run

```
   caller code
       │
       │ raise SchemaMismatchError(...)     ← subclass of DataIntegrityError,
       │                                       registered with a code + remediation
       ▼
 recording() context manager
       │  - was buffering logs in memory (ring buffer, bounded size)
       │  - exception escapes → BundleWriter.write() fires
       │      writes manifest.json (error payload + traceback + env info)
       │      writes recent.log   (the buffered log lines)
       ▼
 run_main() / @as_main boundary handler
       │  - inspects exception category → picks exit_code
       │  - prints message + remediation to stderr
       │  - optionally writes ci-summary.json for Jenkins/Gradle to read
       ▼
   sys.exit(exit_code)
```

## Why the registry is separate from the exception classes themselves

Category (`UserError` vs `InfrastructureError` etc.) is a Python-level
`isinstance` fact and needs to be cheap to check at runtime — it lives on the
class hierarchy itself. Metadata like the human-facing error *code*,
*remediation text*, and any per-class *retry override* is administrative and
project-specific, and multiple packages might want to register into either a
shared catalog or their own — so it lives in a separate registry keyed by
class, not baked into `exceptions.py`.

## Why bundles are opt-in-by-failure, not always-on

Always writing full diagnostic detail (env vars, full log history, file
snapshots) on every run is either too noisy to search through, or gets
disabled in practice because it's expensive. Buffering in memory and only
persisting on failure means you get complete forensics exactly when you need
them, at effectively zero cost on the (overwhelming majority of) successful
runs.
