"""Black-box smoke of an extracted, installed Linux Community source preview."""
import argparse
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request


def request(url, **kwargs):
    with urllib.request.urlopen(urllib.request.Request(url, **kwargs), timeout=3) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    # Import from the installed environment, not the checkout used to build it.
    from PIL import Image
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(['bash', str(root / 'scripts/run-linux.sh')], cwd='/',
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Preview launcher exited before readiness')
                try:
                    status = json.loads(request('http://127.0.0.1:8000/api/status'))
                    page = request('http://127.0.0.1:8080/').decode()
                    if status.get('version') == args.version and 'Lumqenix' in page:
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError('Preview did not become ready')
            assert json.loads(request('http://127.0.0.1:8000/api/edition'))['edition'] == 'community'
            assert json.loads(request('http://127.0.0.1:8000/api/brand'))['studio']
            image = io.BytesIO()
            Image.new('RGB', (16, 12), (120, 90, 70)).save(image, format='PNG')
            boundary = 'lumqenix-preview-smoke-boundary'
            body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="sample.png"\r\nContent-Type: image/png\r\n\r\n'.encode()
                    + image.getvalue() + f'\r\n--{boundary}--\r\n'.encode())
            encoded = request('http://127.0.0.1:8000/api/enhance/image', data=body,
                              headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
            with Image.open(io.BytesIO(encoded)) as output:
                assert output.format == 'PNG' and output.size == (32, 24)
        except Exception:
            log.seek(0)
            print(log.read().decode(errors='replace'))
            raise
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        for port in (8000, 8080):
            with socket.socket() as probe:
                probe.settimeout(0.5)
                assert probe.connect_ex(('127.0.0.1', port)) != 0, f'Launcher left port {port} listening'
    print(json.dumps({'installed_version': args.version, 'localhost_api_ui': True,
                      'real_image_dimensions': [32,24], 'shutdown_cleanup': True}))


if __name__ == '__main__':
    main()
