# Lumqenix Community + Pro: repository and licensing strategy

Status: Community is public; the separate private Pro repository exists with
experimental Fidelity Guard code and private CI. No finished commercial
product or validated installable Pro release is claimed.

## Non-negotiable separation

- **Community repository:** `sudipdasin/lumqenix-ai`, currently PUBLIC and MIT-licensed for original project source. The public history still needs a complete security/third-party rights audit. Community must be independently installable with no Pro license.
- **Pro repository (existing):** `sudipdasin/lumqenix-pro`, confirmed PRIVATE. It contains experimental proprietary Fidelity Guard code, contract checks and private CI; paid UI, production licensing, models, and commercial installers are future work. **Never add Pro code to the public repository.**
- One-way dependency: Pro consumes a **pinned, signed or SHA-verified Community release/tag**. Community must never import or depend on Pro. Private CI builds the Pro edition from its own source and the pinned Community dependency.
- Do not blindly mirror private branches to public. Synchronize **public core changes upstream** through reviewed pull requests; consume the public core downstream through versioned tags and an automated dependency-update PR. Synchronization is of shared code, **not** of private-only commits or assets.
- Both builds expose a clear edition name. Public downloads, issue tracker, documentation, SDK contracts, tests and release notes stay usable without Pro.
- No proprietary files, private model weights, customer data, license-signing keys, payment secrets, or commercial telemetry credentials in Community source, tags, workflow logs, fixtures, or build artifacts.

## Repository topology

```text
lumqenix-ai/                 PUBLIC Community source; audit before releases
  backend/ frontend/ config/ tests/ docs/
  scripts/check_edition_boundary.py
  .github/workflows/           Public CI, reproducible public release
lumqenix-pro/                Existing PRIVATE repo, no commercial release
  pro_backend/               Experimental proprietary Fidelity Guard
  tests/                     Private regression and compatibility tests
  scripts/                   One-way Community pin/sync tools
  community.lock             Exact pinned Community development commit
  .github/workflows/         Private tests and reviewed update proposals
  planned/                   Pro UI, licensing, models, packaging (not built)
```

## Product boundaries

**Community (permanently free):** classic image/video enhancement, supported open-model adapters, local processing, basic portrait tools, batch/API fundamentals where implemented, export, documented configuration, reproducible tests, accessibility, and community contributions. Do not deliberately degrade existing Community features or move previously open features behind a paywall without an explicit public policy decision.

**Pro candidates (research, not promised):** temporal video restoration with cross-frame consistency; intelligent subject-aware restoration with inspectable masks; professional color-managed batch pipelines and scene-aware presets; automated fidelity risk detection with reversible comparisons; large-media tiling and resumable jobs; enterprise workflow integrations. Each must pass real-model quality, rights/licensing, CPU/memory, privacy, and user-value gates. Avoid unsupported claims of unique capabilities.

**Monetization:** local-first perpetual or subscription license options to evaluate; offline grace period, transparent privacy policy, clear trial limitations, no remote upload without opt-in. Community remains functional if Pro licensing infrastructure is unavailable. Never put signing secrets in client code; server-side entitlements must not be confused with encryption or copy protection.

## Publication and licensing gate

1. Inventory all files and the **entire Git history** for secrets, PII, proprietary assets, and third-party rights. Removing a file in a later commit does not remove it from history.
2. The Community development branch now has an MIT license for **original project source** and contributor/security policies. Before public distribution, audit provenance, all upstream dependencies and third-party assets; do not assume rights over third-party code or weights.
3. Run `python scripts/check_edition_boundary.py` in Community CI before packaging and publication. This guard checks tracked paths only; also use secret scanning, license scanning, artifact inspection, and history review.
4. Keep the existing Pro repository **private**; verify access limits, private CI tokens, reviewer protections and artifact retention. Never place private assets in public forks or pull requests.
5. Pin Community dependency in Pro; test both editions independently in Linux VM CI, including actual pretrained models, FFmpeg, 4 GiB RSS ceilings, and install/uninstall. Gate release tags on passing evidence.
6. Publish Community beta only when reproducible installable artifacts pass tests. Do not publish Pro binaries or final releases without an explicit release decision.

## Contributor and IP policy

Public contributors retain their rights under the chosen OSS license; Pro must respect that license and all upstream model licenses. Prefer permissive OSS licensing if commercial combination is a key goal, but decide only after a dependency/license audit. Do not silently demand copyright assignment. If using copyleft dependencies, obtain legal review before linking or distributing closed-source components. Trademark and commercial license terms are separate from the Community source license.

## Current execution status

The Community source repository is currently PUBLIC and carries an MIT license for original code. Its full history and third-party rights remain to be audited before an additional certified release. The separate `lumqenix-pro` GitHub repository exists and remains PRIVATE, with experimental Fidelity Guard and reviewed one-way sync tooling. VM testing, private credential configuration, commercial entitlements, complete installers and release verification remain open.
