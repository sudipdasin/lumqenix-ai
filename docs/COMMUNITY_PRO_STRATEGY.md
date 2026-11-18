# Lumqenix Community + Pro: repository and licensing strategy

Status: architecture decision; **not** a claim that a Pro product, license, or public repository already exists.

## Non-negotiable separation

- **Community repository:** `sudipdasin/lumqenix-ai` (currently PRIVATE; make public only after license, security and history audits). Community must be useful and independently installable. No license server or Pro account is needed for its core features.
- **Pro repository (proposed):** `sudipdasin/lumqenix-pro`, PRIVATE from creation. Contains proprietary algorithms, premium UI, licensing client, private tests, private assets, commercial packaging and deployment. **Do not create a Pro directory or Pro branch in the public repository.**
- One-way dependency: Pro consumes a **pinned, signed or SHA-verified Community release/tag**. Community must never import or depend on Pro. Private CI builds the Pro edition from its own source and the pinned Community dependency.
- Do not blindly mirror private branches to public. Synchronize **public core changes upstream** through reviewed pull requests; consume the public core downstream through versioned tags and an automated dependency-update PR. Synchronization is of shared code, **not** of private-only commits or assets.
- Both builds expose a clear edition name. Public downloads, issue tracker, documentation, SDK contracts, tests and release notes stay usable without Pro.
- No proprietary files, private model weights, customer data, license-signing keys, payment secrets, or commercial telemetry credentials in Community source, tags, workflow logs, fixtures, or build artifacts.

## Repository topology

```text
lumqenix-ai/                 Community source; public only after audit
  backend/ frontend/ config/ tests/ docs/
  scripts/check_edition_boundary.py
  .github/workflows/           Public CI, reproducible public release
lumqenix-pro/                Separate private repository (to create)
  pro_backend/               Proprietary processing engines
  pro_frontend/              Pro-only workflows and UI
  pro_models/                Private licensed resources (not in public Git)
  licensing/                 Entitlement adapters (never signing keys)
  packaging/                 Private installer and release pipeline
  tests/                     Pro and Community compatibility suites
  community.lock             Exact Community commit/tag and checksum
```

## Product boundaries

**Community (permanently free):** classic image/video enhancement, supported open-model adapters, local processing, basic portrait tools, batch/API fundamentals where implemented, export, documented configuration, reproducible tests, accessibility, and community contributions. Do not deliberately degrade existing Community features or move previously open features behind a paywall without an explicit public policy decision.

**Pro candidates (research, not promised):** temporal video restoration with cross-frame consistency; intelligent subject-aware restoration with inspectable masks; professional color-managed batch pipelines and scene-aware presets; automated fidelity risk detection with reversible comparisons; large-media tiling and resumable jobs; enterprise workflow integrations. Each must pass real-model quality, rights/licensing, CPU/memory, privacy, and user-value gates. Avoid unsupported claims of unique capabilities.

**Monetization:** local-first perpetual or subscription license options to evaluate; offline grace period, transparent privacy policy, clear trial limitations, no remote upload without opt-in. Community remains functional if Pro licensing infrastructure is unavailable. Never put signing secrets in client code; server-side entitlements must not be confused with encryption or copy protection.

## Publication and licensing gate

1. Inventory all files and the **entire Git history** for secrets, PII, proprietary assets, and third-party rights. Removing a file in a later commit does not remove it from history.
2. The Community development branch now has an MIT license for **original project source** and contributor/security policies. Before public distribution, audit provenance, all upstream dependencies and third-party assets; do not assume rights over third-party code or weights.
3. Run `python scripts/check_edition_boundary.py` in Community CI before packaging and publication. This guard checks tracked paths only; also use secret scanning, license scanning, artifact inspection, and history review.
4. Create the Pro repository **private** and restrict collaborators, tokens, CI environments and artifact retention. Never place private assets in public forks or pull requests.
5. Pin Community dependency in Pro; test both editions independently in Linux VM CI, including actual pretrained models, FFmpeg, 4 GiB RSS ceilings, and install/uninstall. Gate release tags on passing evidence.
6. Publish Community beta only when reproducible installable artifacts pass tests. Do not publish Pro binaries or final releases without an explicit release decision.

## Contributor and IP policy

Public contributors retain their rights under the chosen OSS license; Pro must respect that license and all upstream model licenses. Prefer permissive OSS licensing if commercial combination is a key goal, but decide only after a dependency/license audit. Do not silently demand copyright assignment. If using copyleft dependencies, obtain legal review before linking or distributing closed-source components. Trademark and commercial license terms are separate from the Community source license.

## Current execution status

The existing Community repository is still private. MIT-licensed source and Community edition API are implemented on the development branch, but publication still requires a full history and third-party rights audit. A **separate private Pro repository bootstrap** with an experimental Fidelity Guard has been prepared outside this repository; the GitHub Pro repository itself is **not created yet**. Reviewed upstream synchronization, VM tests, installer verification and commercial licensing remain open.
