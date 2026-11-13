# Portable execution

Commands below run from the extracted skill folder. From any other working directory use the absolute path to `scripts/engine.py`. `python` means an available Python 3.11–3.13 interpreter (`python3` or `py -3.13` may be the local command). An agent with shell access can perform setup; a chat-only environment cannot execute these helpers.

```text
python scripts/engine.py doctor
python scripts/engine.py bootstrap
python scripts/engine.py profile-check --profile paleon
python scripts/engine.py init --profile paleon --project /chosen/new-video --topic "How did early humans care for injuries?"
python scripts/engine.py voice --project /chosen/new-video
python scripts/engine.py scene-seed --project /chosen/new-video
python scripts/engine.py validate --project /chosen/new-video
python scripts/engine.py render --project /chosen/new-video
```

Use real paths appropriate to the host; do not paste `/chosen/...` literally. Initialization and validation need only the standard library. `bootstrap` creates a virtual environment in the user's cache and installs exact direct dependency versions from `requirements.txt`. Transitive versions are resolved by pip; this is not a fully locked, bit-reproducible environment. Failed installation never writes a success marker; rerun bootstrap after resolving the reported error. Voice/render automatically bootstrap when necessary. `--no-setup` makes those commands fail instead of downloading/installing.

Cache override: `YOUTUBE_ENGINE_CACHE`. Defaults follow LOCALAPPDATA on Windows, Library/Caches on macOS, XDG_CACHE_HOME or ~/.cache on Linux. The cache stores runtime and models, never API secrets. Skill folders can be read-only. A Python ABI/platform/requirements fingerprint selects the runtime; no global pip installs or machine-specific paths are needed.

Kokoro uses a versioned public release. Model download is streamed to a temporary file, SHA-256 checked, then atomically moved into cache. Existing corrupt models cause an explicit error (do not silently overwrite them). Expected digests are recorded in `scripts/models.py`; only update them with independently verified new files. Models are not included in the ZIP. First-time downloads can be large (~354 MB combined); report this before voice generation when relevant. Dependency/model downloads do not buy service credits.

FFmpeg comes from the pinned `imageio-ffmpeg` package, or an explicit `YOUTUBE_ENGINE_FFMPEG` executable path. No system FFmpeg is required on supported wheels. Unsupported hardware/platform wheels need a compatible local Python/FFmpeg installation; surface the actual failure. Do not promise compatibility before a smoke test.

Research and image generation use the host agent's available connectors/browser/image tools. This package contains no paid API credentials and no image generation API integration. External audio can be provided as `voiceover.wav` plus matching `voiceover.srt`; it must be PCM WAV readable by Python's wave module. Convert other formats explicitly. CapCut editing is optional: use the user's installed compatible tool and verify the resulting draft separately; no bundled CapCut bridge is claimed.

Redistribution: `THIRD_PARTY.md` records upstream code and model references. The helper test suite runs with `python -B -m unittest discover -s tests -v`; synthesis/render smoke tests are additional integration checks, not supplied by a mocked unit test.
