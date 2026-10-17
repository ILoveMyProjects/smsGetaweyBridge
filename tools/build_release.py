"""Build a manually installable integration ZIP and release notes from an existing Git tag.

This script needs only Python's standard library; it does not access GitHub or Android.
The GitHub Action that invokes it MUST gate publishing behind all CI validators.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / 'custom_components' / 'smsgetaweybridge'


def prepare_release(tag: str, out: Path) -> tuple[Path, Path, Path]:
    if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise ValueError(f'Unsupported tag format: {tag!r}; expected vX.Y.Z')
    version = tag.removeprefix('v')
    manifest = json.loads((INTEGRATION / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('version') != version:
        raise ValueError(f'Git tag {tag} mismatches integration version {manifest.get("version")!r}')
    if not (INTEGRATION / '__init__.py').exists():
        raise ValueError('Missing __init__.py')
    if not (INTEGRATION / 'manifest.json').exists():
        raise ValueError('Missing manifest.json')

    changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    match = re.search(rf'^##\s+{re.escape(version)}\b[^\n]*\n(?P<notes>.*?)(?=^##\s+\d+\.\d+\.\d+\b|\Z)',
                      changelog, flags=re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError(f'CHANGELOG.md has no section for {version}')

    out.mkdir(parents=True, exist_ok=True)
    archive = out / f'smsGetaweyBridge-{tag}.zip'
    files = [file for file in INTEGRATION.rglob('*') if file.is_file()
             and '__pycache__' not in file.parts and file.suffix != '.pyc']
    if not files:
        raise ValueError('No integration files found')
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED, compresslevel=9) as zipped:
        for file in sorted(files):
            # Correct install layout after extracting into the HA config directory.
            zipped.write(file, file.relative_to(ROOT).as_posix())
    with ZipFile(archive) as zipped:
        bad_file = zipped.testzip()
        if bad_file:
            raise ValueError(f'ZIP integrity failure at {bad_file}')

    checksum = out / 'SHA256SUMS.txt'
    checksum.write_text(f'{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n', encoding='utf-8')
    notes = out / 'RELEASE_NOTES.md'
    notes.write_text(f'# smsGetaweyBridge {tag}\n\n' + match.group('notes').strip() +
                     '\n\n**Preview**: live Home Assistant + Android integration tests are still required.\n'
                     if version.startswith('0.') else
                     f'# smsGetaweyBridge {tag}\n\n' + match.group('notes').strip() + '\n',
                     encoding='utf-8')
    return archive, checksum, notes


def main() -> None:
    parser = argparse.ArgumentParser(description='Build validated GitHub release assets')
    parser.add_argument('--tag', required=True)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    for file in prepare_release(args.tag, args.output_dir):
        print(file)


if __name__ == '__main__':
    main()
