# Roadmap

Each `## M<n>` section below maps to one **GitHub Milestone**. Each checkbox
maps to one **GitHub Issue** — copy the checkbox text into an issue title,
tag it with the milestone, and check it off here (or just track via the
Milestone progress bar GitHub already gives you). Rough size is noted so you
can plan how much to bite off in a sitting.

Status legend: ✅ scaffolded in this repo already · ⬜ not started

---

## M0 — Project Scaffolding & Tooling
*Goal: a repo that installs, lints, type-checks, and tests cleanly on a fresh clone.*

- [x] `pyproject.toml` with `uv`, Python 3.12+, hatchling build backend
- [x] `src/` layout with `faultline` package
- [x] Ruff + mypy strict config
- [x] Pytest config with coverage
- [ ] `uv sync` verified on a clean machine/container
- [ ] Pre-commit hooks (ruff, mypy, trailing whitespace) — optional but recommended
- [ ] GitHub Actions CI workflow running on push/PR *(scaffolded, needs a live run)*
- [ ] Branch protection on `main` requiring CI to pass

**Size:** small — mostly done, just needs verifying against a real GitHub repo.

---

## M1 — Core Exception Taxonomy
*Goal: `ToolchainError` and its four subclasses, fully tested.*

- [x] `ToolchainError` base class with `context`, `remediation`, `to_dict()`
- [x] `UserError`, `InfrastructureError`, `DataIntegrityError`, `InternalError`
- [x] Unit tests for exit codes, retryable defaults, serialization
- [ ] Docstring pass: make sure every class's docstring alone explains when
      to use it (this docstring becomes user-facing catalog text later)
- [ ] Decide & document exit code numbering convention (currently 2/3/4/5)

**Size:** small — core is done; this milestone is really "polish + freeze the API."

---

## M2 — Error Registry & Catalog Metadata
*Goal: `@error_catalog.register(...)` decorator with code uniqueness + lookups.*

- [x] `ErrorSpec` dataclass + `ErrorCatalog` class
- [x] `register()` decorator: code uniqueness check, type check, retryable override
- [x] `spec_for()`, `class_for_code()`, `all_specs()`
- [x] Unit tests covering duplicate codes, invalid classes, sorting
- [ ] Decide code-namespacing convention for multi-package setups
      (e.g. `WRAPGEN-014` vs `wrapgen.schema.mismatch`)
- [ ] Add a `validate()` method that checks all registered codes match the
      namespacing convention (useful as a CI lint step later)

**Size:** small — core is done; remaining items are conventions/polish.

---

## M3 — Diagnostic Black Box Recorder
*Goal: `recording()` context manager that captures logs and writes bundles only on failure.*

- [x] `_RingBufferHandler` (bounded in-memory log buffer)
- [x] `BundleWriter` (manifest.json + recent.log on failure)
- [x] `recording()` context manager, yields correlation ID
- [x] Unit tests: no bundle on success, bundle written on failure, correlation ID reuse
- [ ] Add optional file-snapshot capture (e.g. "attach these 3 input files
      to the bundle if they exist") — directly targets the "corrupted XML"
      support case
- [ ] Add a `max_bundle_age_days` cleanup helper so bundle dirs don't grow
      unbounded on long-lived CI agents
- [ ] Document recommended Jenkins "archive artifacts" glob for bundle dirs

**Size:** medium — core loop works; file-snapshot capture is the interesting remaining piece.

---

## M4 — Boundary Layer & Exit Code Contract
*Goal: one top-level handler per CLI entry point; consistent exit codes + CI summary JSON.*

- [x] `run_main()` / `@as_main`
- [x] Exit code mapping from exception category
- [x] Optional `ci_summary_path` JSON output
- [x] Unit tests: UserError exit code, unexpected exception exit code, success passthrough
- [ ] Add a `--faultline-ci-summary <path>` convention doc so all three of
      your real packages emit summaries to a predictable location
- [ ] Add Gradle-side example: reading the CI summary JSON to decide
      "retry this stage" vs "fail the build" vs "flag for triage"

**Size:** small-medium — core is done; the Gradle-integration example is the valuable remaining part.

---

## M5 — Structured Logging Integration
*Goal: JSON-structured logs with correlation ID propagated across subprocess boundaries.*

- [ ] `logging_utils.py`: a `configure_json_logging()` helper (stdlib `logging`
      + JSON formatter, no hard dependency on structlog/orjson unless installed)
- [ ] Correlation ID propagation via env var across `subprocess.run()` calls
- [ ] Example: Gradle task → Python subprocess → REST client, all sharing one
      correlation ID end to end
- [ ] Unit tests for the JSON formatter output shape

**Size:** medium — the subprocess correlation propagation is the novel part; worth taking your time on it.

---

## M6 — Retry Policy Engine
*Goal: retry eligibility driven declaratively by the registry, not a separate decorator config.*

- [ ] `retry.py`: `@retryable_call(...)` decorator that reads `spec.retryable`
      from the registry instead of taking its own exception list
- [ ] Optional `tenacity` integration (install via `faultline[retry]`)
- [ ] Backoff/jitter defaults tuned for "flaky REST call in CI" scenarios
- [ ] Unit tests: retryable class retries N times then raises; non-retryable
      class raises immediately

**Size:** medium — directly solves the "REST timeouts mishandled as code errors" pain point.

---

## M7 — Auto-Generated Error Catalog
*Goal: `faultline catalog build` renders all registered errors into docs.*

- [ ] `catalog.py`: render `ErrorCatalog.all_specs()` to Markdown
- [ ] Wire up `faultline catalog build --catalog myapp.errors:error_catalog`
      in `cli.py` (replacing the current placeholder)
- [ ] Support merging multiple catalogs (for your three-package setup)
- [ ] Optional: simple static HTML output for hosting alongside docs
- [ ] Add this as a CI step so the catalog doc can't go stale

**Size:** medium — this is the piece most directly aimed at reducing support ticket volume.

---

## M8 — Documentation & Examples
*Goal: someone unfamiliar with the project can adopt it in under 30 minutes.*

- [x] README quickstart
- [x] `docs/architecture.md`
- [x] `examples/minimal_cli.py`
- [ ] "Migrating an existing package to faultline" guide, written against
      one of your real work packages' patterns (genericized)
- [ ] Example Jenkins pipeline snippet consuming exit codes + CI summary JSON
- [ ] CONTRIBUTING.md (even if it's just you for now — future you will want it)

**Size:** medium — mostly writing; the migration guide is the highest-value piece.

---

## M9 — v1.0 Release & Packaging
*Goal: a tagged, installable release.*

- [ ] Finalize public API (audit `__all__`, freeze method signatures)
- [ ] `CHANGELOG.md` following Keep a Changelog format
- [ ] GitHub Actions release workflow: build + publish to PyPI on tag push
- [ ] Semantic version tag `v1.0.0`
- [ ] Announce/adopt internally: point one real package's CI at this library
      via a git dependency before doing a full PyPI-based rollout

**Size:** small-medium — mostly process, but don't skip the API freeze step.

---

## Suggested working order

M0 → M1 → M2 → M3 → M4 are effectively done as scaffolding (this repo). Your
first real work session should be **verifying M0 end-to-end** (fresh clone,
`uv sync`, CI green) since everything else assumes that foundation is solid.
After that, **M6 (retry) and M7 (catalog)** are the two milestones with the
most direct payoff against your original support-ticket problem — prioritize
those over M5/M8 if you want to see impact quickly.
