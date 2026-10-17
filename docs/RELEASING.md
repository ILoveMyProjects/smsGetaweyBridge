# Releasing smsGetaweyBridge (GitHub + HACS)

Repository: <https://github.com/ILoveMyProjects/smsGetaweyBridge>

## Versioning

- Use annotated Git tags `vX.Y.Z` (for example, `v0.2.1`).
- Keep `custom_components/smsgetaweybridge/manifest.json` `version` equal to the tag **without** the leading `v`.
- Update `CHANGELOG.md` with a section starting `## X.Y.Z` before tagging.
- **Do not move or force-push an existing release tag.** If a version or tag already exists, publish a **new version** after updating the manifest and changelog (for example, `v0.1.2`).
- During the current `0.x` preview series, the automated workflow marks releases as *pre-release*. Remove this policy deliberately when the project reaches stable status.

## Before tagging

1. Check the [repository](https://github.com/ILoveMyProjects/smsGetaweyBridge) and [existing releases](https://github.com/ILoveMyProjects/smsGetaweyBridge/releases) for conflicts. **Do not blindly overwrite unknown repository content.**
2. Ensure the project files (including `.github/workflows/tests.yml`, `hacs.json` and `custom_components/`) are committed to the default branch.
3. Run the offline tests locally: `python -m unittest discover -s tests -v` and `python -m compileall -q custom_components` (aiohttp is required by unit tests). CI will run these again.
4. Make sure GitHub Actions are enabled, and the repository workflow has permission to create releases via the job-scoped `contents: write` permission. Depending on repository/org policy, GitHub may restrict workflow permissions.
5. Wait for CI validation of the default-branch commit. The tag workflow **also re-runs** the checks before publishing a release.

## First release / subsequent releases

Run in a local Git clone of the repository after merging the reviewed changes into the default branch:

```bash
git fetch --tags origin
git status --short
git tag -l 'v*'
# Ensure v0.2.1 does not already exist before executing the next lines.
git tag -a v0.2.1 -m 'smsGetaweyBridge v0.2.1'
git push origin v0.2.1
```

On a `push` for a `v*` tag, the single `.github/workflows/tests.yml` workflow runs these jobs:

1. Python syntax + unit tests.
2. HACS integration repository validation.
3. Home Assistant Hassfest integration validation.
4. **Only if all three pass:** verify tag format and manifest version, build a manual-install `smsGetaweyBridge-vX.Y.Z.zip`, calculate `SHA256SUMS.txt`, and publish a GitHub Release with notes extracted from the matching changelog section.

If any check fails, the release job is skipped. `workflow_dispatch` and pull requests **cannot publish releases**. The generated manual-install ZIP has the same `custom_components/smsgetaweybridge/` directory layout expected under the Home Assistant config directory. HACS reads the tagged repository, not that ZIP asset (unless you change the HACS manifest in a later version).

> The workflow cannot retroactively run against tags that were pushed before the workflow was present. If a tag already exists, do not force-move it; create a new version/tag once the repository is ready.

## Verify the published release

1. Open [Actions](https://github.com/ILoveMyProjects/smsGetaweyBridge/actions) and confirm the tag workflow succeeded in all jobs.
2. Open [Releases](https://github.com/ILoveMyProjects/smsGetaweyBridge/releases) and check the tag, version, release notes, ZIP, and `SHA256SUMS.txt`.
3. Download the ZIP, run `sha256sum -c SHA256SUMS.txt` in the directory holding the ZIP and checksum, and inspect that it contains `custom_components/smsgetaweybridge/manifest.json`.
4. Test installation in HACS as a Custom repository → Integration using the selected release version. Complete GUI setup against a real Local Server and test one SMS to a number you own.

## GitHub repository settings (manual)

**Before running HACS validation**, open the GitHub repository page, click **About → Edit (gear icon)**, fill in the **Description** with `Local Home Assistant SMS integration for SMS Gateway for Android`, then add repository **Topics**: `home-assistant`, `hacs`, `sms`, `sms-gateway`, `android`. Save. Ensure Issues are enabled (Settings → General → Features). These settings live in GitHub repository metadata and cannot be applied by uploading a ZIP or editing README.

Brand assets are shipped in `custom_components/smsgetaweybridge/brand/icon.png` and `dark_icon.png` for Home Assistant 2026.3 and later. HACS custom repositories and the default HACS catalog are different: joining the default catalog requires additional brand/review requirements and is **not** automatic with releases.

## Troubleshooting

- **Manifest version/tag mismatch:** update the manifest and changelog, commit, create a **new** tag.
- **Tests fail:** no release is published; fix code and bump the version for a subsequent tag (avoid editing or moving released tags).
- **HACS/Hassfest validation fails:** inspect the corresponding job logs; a `v*` tag does not bypass validation.
- **GH release fails for permissions:** adjust the repository's Actions workflow permissions/policies or publish manually after successful validation.
- **HACS does not show a release:** confirm GitHub release was published and HACS updated its repository information; prerelease visibility can vary with client settings/version.
