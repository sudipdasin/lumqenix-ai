"""Studio Lite client-side functionality and accessibility contracts."""
from pathlib import Path

HTML = (Path(__file__).resolve().parents[2] / "frontend/index.html").read_text(
    encoding="utf-8"
)


def test_interactive_wipe_has_both_images_and_slider():
    assert 'id="wipeBefore"' in HTML
    assert 'id="wipeAfter"' in HTML
    assert 'id="split" type="range"' in HTML
    assert "style.setProperty('--split'" in HTML
    assert "style.aspectRatio=im.width" in HTML


def test_cancel_button_wired_to_abort_signal():
    assert 'id="cancel" type="button" disabled' in HTML
    assert "activeController=new AbortController()" in HTML
    assert "signal:activeController.signal" in HTML
    assert "activeController.abort()" in HTML
    assert "e.name==='AbortError'" in HTML
    assert "'cancel').disabled=true" in HTML


def test_public_upload_cap_checked_before_fetch():
    assert "maxUploadBytes=Number(s.max_upload_bytes)||Infinity" in HTML
    assert "if(isPublicPreview&&f.size>maxUploadBytes)" in HTML
    assert "File is too large for the online preview" in HTML


def test_unavailable_neural_modes_disabled_when_server_reports_no_models():
    assert "function updateCapabilities()" in HTML
    assert "option.disabled=" in HTML
    assert "modelReady" in HTML
    assert "espcnReady" in HTML
    assert "fsrcnnReady" in HTML


def test_still_supports_synthetic_png_e2e_demo():
    assert 'id="sample"' in HTML
    assert "canvas.toBlob(resolve,'image/png')" in HTML
    assert "Synthetic sample loaded" in HTML
