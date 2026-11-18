"""Public ABI contract: free features must not depend on Pro."""
from app.edition import COMMUNITY_CAPABILITIES, community_manifest


def test_community_manifest_is_explicit_and_safe():
    manifest = community_manifest()
    assert manifest["edition"] == "community"
    assert manifest["contract_version"] == 1
    assert manifest["license"] == "MIT"
    assert manifest["proprietary_code_bundled"] is False
    assert set(manifest["capabilities"]) == set(COMMUNITY_CAPABILITIES)
    assert not any(name.startswith(("pro-", "commercial-", "premium-")) for name in manifest["capabilities"])


def test_caller_cannot_mutate_module_capabilities():
    returned = community_manifest()
    returned["capabilities"].append("injected-premium")
    assert "injected-premium" not in community_manifest()["capabilities"]


def test_edition_endpoint_stays_community():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/edition")
    assert response.status_code == 200
    assert response.json() == community_manifest()
    status = client.get("/api/status")
    assert status.status_code == 200
    assert status.json()["edition"] == "community"
