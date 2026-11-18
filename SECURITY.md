# Security policy — Lumqenix Community

## Supported versions

Security fixes target the current maintained Community development line and
published supported releases. Development snapshots are not production releases.

## Report privately

Please use GitHub's **Report a vulnerability** / private security advisory
feature for this repository when available. Do not disclose exploitable details,
tokens, private model assets, or other users' data in public issues or PRs.
If private advisories are unavailable, ask maintainers for a secure reporting
channel through a non-sensitive issue without posting exploit material.

## Security model

The current API is intended for **local, single-user** use on loopback only.
It is not authenticated for internet-facing multi-user deployment. Keep one
worker, enforce documented upload and output limits, inspect untrusted FFmpeg
inputs, and do not mount a public hostname without separate isolation and
authentication. Model files and optional pretrained downloads are third-party
resources and require provenance, license and checksum verification.

Premium signing keys, payment credentials, Pro source and private licensing
artifacts must never be committed to this Community repository or its history.
The source-boundary and publication scanners are **defense in depth** only,
not proof that a repository is safe to publish.
