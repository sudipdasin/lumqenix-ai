# Community public-release gate (mandatory)

**Current state:** repository remains private. This checklist must be
completed before changing its GitHub visibility or publishing binaries.

- [ ] Run `python scripts/check_edition_boundary.py` on intended release HEAD.
- [ ] Run `python scripts/audit_publication.py --history` in a **full clone**
      with all intended refs. Its high-confidence detections are not a
      complete PII, copyright, or secret scan.
- [ ] Examine *all* reachable Git history for sensitive user paths, personal
      data, secrets, and proprietary assets; rotate any exposed credentials
      before publication, even if a later commit deleted them. Check tags,
      issues, artifacts, forks and LFS separately.
- [ ] Inventory third-party model weights, media fixtures, libraries, and
      transitive licenses; verify distribution rights and attribution.
- [ ] Confirm `LICENSE` applies only to code controlled by project
      contributors, not third-party media, pretrained weights or trademarks.
- [ ] Run public test matrix (Python 3.10/3.12, optional neural inference,
      frontend, video/FFmpeg, CPU budget and release evidence). Inspect real
      execution logs, artifacts and accurate skips.
- [ ] Test install, uninstall, UI, permissions and baseline quality in a Linux
      VM plus an actual 4 GiB RAM CPU machine before claiming that requirement.
- [ ] Create `lumqenix-pro` separately with **private visibility**, restricted
      access, branch protections, commercial-only source and a pinned
      dependency on the Community repository.
- [ ] Create Pro CI with independent entitlement, regression and dependency
      compatibility checks. Never mirror Pro content to the public repository.
- [ ] Confirm public release links and packages include no secret, private
      models, unpublished licensed data or internal config.
- [ ] Human maintainers approve the publication state and release notes.

CI must fail closed on any detected issue; lack of findings does **not** make
publication automatically safe. Do not automatically mark a dev build as RC.
