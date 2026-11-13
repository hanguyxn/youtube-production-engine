"""Versioned model cache. No binary is written into the installed skill."""
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.request

BASE = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
FILES = {
    'kokoro-v1.0.onnx': '7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5',
    'voices-v1.0.bin': 'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d',
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as src:
        for block in iter(lambda: src.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ensure_models(directory, allow_download=True):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, expected in FILES.items():
        target = directory / name
        if target.exists():
            if digest(target) != expected:
                raise ValueError(f'Corrupt model: {target}. Remove or move that file, then retry setup.')
            continue
        if not allow_download:
            raise ValueError(f'Missing model: {target}; run voice without --no-setup once online.')
        print(f'Downloading and verifying {name}', flush=True)
        fd, temp_name = tempfile.mkstemp(prefix='.download-', dir=directory)
        try:
            with os.fdopen(fd, 'wb') as dst, urllib.request.urlopen(BASE + name, timeout=120) as src:
                while block := src.read(1024 * 1024):
                    dst.write(block)
            if digest(temp_name) != expected:
                raise ValueError(f'SHA-256 mismatch: {name}; download was not installed.')
            os.replace(temp_name, target)
        finally:
            Path(temp_name).unlink(missing_ok=True)
    return directory / 'kokoro-v1.0.onnx', directory / 'voices-v1.0.bin'
