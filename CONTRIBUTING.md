# Contributing to Lumqenix Community

Thanks for improving the free, local-first Lumqenix application. Core features
must remain independently usable without a commercial account or private source.

## Quick start

1. Create an issue or discussion before a large design change.
2. Fork the Community repository; branch from the current public development base.
3. Install Python 3.10+ and FFmpeg. In `backend/`, create a virtual environment,
   install `requirements.txt`, then install `pytest httpx`.
4. Run `python -m pytest -q tests` from `backend/`. Real model tests require
   explicit approved model downloads; skips are **not** proof of inference.
5. Run `python scripts/check_edition_boundary.py` and
   `python scripts/audit_publication.py` from the repository root.
6. Submit a focused PR with a description, tests, benchmark evidence where
   applicable, and a changelog entry. State what was not tested.

## Codebase

- `backend/app/`: Community API and processing engines.
- `backend/tests/`: regression and integration tests.
- `frontend/`: self-hosted public UI.
- `backend/scripts/`: model benchmarks and quality-evidence tools.
- `scripts/`: open-source/publication safety tooling.
- `docs/`: architecture and Community/Pro separation policy.

Do not add private licensing keys, proprietary code, paid-only models, user
datasets, personal information or commercial service credentials to public
branches, commits, issues, artifacts or tests. Commercial enhancements belong
in the **separate private Pro repository** and must consume Community through
the documented edition contract.

## Quality and respectful collaboration

Prefer small, reversible commits and regression tests. Record exact model
weights (hashes and rights), realistic reference-image metrics, CPU performance,
peak memory, supported OS and FFmpeg versions. Do not claim unsupported fidelity
improvements. Before introducing a dependency, describe its license and data
handling. Keep accessible UI and documented offline workflows.

Contributions to this repository are made under its MIT license; you retain
your copyright. No contributor license agreement or copyright transfer is required.
See [SECURITY.md](SECURITY.md) for vulnerability reporting and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for collaboration expectations.
