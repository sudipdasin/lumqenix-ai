from app.hardware import detect_hardware

def test_hardware_has_cpu_fallback():
    info = detect_hardware()
    assert info["cpu"] is True
    assert info["recommended"] in ("cpu", "gpu")
    assert isinstance(info["providers"], list)
