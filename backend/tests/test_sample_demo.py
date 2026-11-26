"""UI demo must create opt-in synthetic media, not upload user files by default."""
from pathlib import Path

HTML = (Path(__file__).resolve().parents[2] / "frontend/index.html").read_text(
    encoding="utf-8"
)


def test_synthetic_image_demo_is_present():
    assert 'id="sample"' in HTML
    assert "canvas.toBlob(resolve,'image/png')" in HTML
    assert "lumqenix-synthetic-sample.png" in HTML
    assert "new DataTransfer()" in HTML


def test_synthetic_demo_remains_opt_in():
    assert "$('sample').onclick=async()=>{" in HTML
    assert "Synthetic sample loaded. Press Enhance & download" in HTML
    assert "$('go').onclick=async()=>{" in HTML
    assert "new File([blob]" in HTML


def test_live_connection_indicator_is_accessible():
    assert 'id="apiConnection" role="status" aria-live="polite"' in HTML
    assert "API: connected" in HTML
    assert "API: offline" in HTML
