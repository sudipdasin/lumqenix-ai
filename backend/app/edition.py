"""Public, stable edition identity. No dependency on private/commercial code."""
from __future__ import annotations

EDITION = "community"
EDITION_CONTRACT_VERSION = 1
COMMUNITY_CAPABILITIES = (
    "classic-image-enhancement",
    "classic-video-enhancement",
    "optional-fsrcnn",
    "optional-espcn",
    "optional-onnx",
    "local-processing-api",
)


def community_manifest() -> dict[str, object]:
    """Describe bundled Community capabilities, not model availability or Pro entitlement."""
    return {
        "edition": EDITION,
        "contract_version": EDITION_CONTRACT_VERSION,
        "license": "MIT",
        "proprietary_code_bundled": False,
        "capabilities": list(COMMUNITY_CAPABILITIES),
    }
