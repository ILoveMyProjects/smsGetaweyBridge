"""Set repo-specific manifest links, before pushing to your own GitHub account.

Standard library only; does not access the network or any device.
"""
import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description="Fill in HACS manifest with your GitHub account")
parser.add_argument("--owner", required=True, help="Real GitHub username/organization")
args = parser.parse_args()
if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", args.owner):
    parser.error("Invalid GitHub account/organization name")
manifest = Path(__file__).resolve().parents[1] / 'custom_components/smsgetaweybridge/manifest.json'
data = json.loads(manifest.read_text(encoding='utf-8'))
base = f'https://github.com/{args.owner}/smsGetaweyBridge'
data.update({
    'documentation': base + '#readme',
    'issue_tracker': base + '/issues',
    'codeowners': ['@' + args.owner],
})
manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Repository metadata updated. Check the URLs before publishing:', base)
