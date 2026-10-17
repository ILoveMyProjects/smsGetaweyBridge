# Developer-only verification

The following commands run **only on a development workstation** or on GitHub Actions ephemeral runners. They are not installation instructions for Home Assistant, Android, or Ubuntu SMS Manager.

```bash
python -m pip install aiohttp
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

`pip install aiohttp` installs a Python library into the runner's current Python environment. The application uses Home Assistant's bundled client session at runtime; `manifest.json` does not request an extra `aiohttp` package. If you do not want any local installations, inspect test results in GitHub Actions instead. `compileall` can create `__pycache__` locally. Tests do not send SMS, connect to your Android phone or access your Home Assistant.
