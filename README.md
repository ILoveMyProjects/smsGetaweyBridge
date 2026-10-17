# smsGetaweyBridge

[![Tests / HACS / Hassfest](https://github.com/ILoveMyProjects/smsGetaweyBridge/actions/workflows/tests.yml/badge.svg)](https://github.com/ILoveMyProjects/smsGetaweyBridge/actions/workflows/tests.yml)
[![GitHub Releases](https://img.shields.io/github/v/release/ILoveMyProjects/smsGetaweyBridge?include_prereleases)](https://github.com/ILoveMyProjects/smsGetaweyBridge/releases)

**A local-first Home Assistant custom integration for [SMS Gateway for Android](https://github.com/capcom6/android-sms-gateway).** Install it through HACS, configure your Android phone's **Local Server** manually, and use its SMS capabilities from Home Assistant.

**Documentation:** English (this page) · [Polski](docs/README_PL.md) · [Security guide](docs/SECURITY.md) · [Release procedure](docs/RELEASING.md) · [Changelog](CHANGELOG.md)

> **Release v1.0.0 (awaiting live verification).** Offline tests have run, but the integration has **not** been validated end-to-end on a live Home Assistant installation and Android SMS Gateway. Test it with your own device before using it for critical alerts. The GitHub repository and release availability must be checked on GitHub after uploading this project.

> **GitHub repository setup:** HACS validation also requires a non-empty repository description and topics. Configure these under GitHub repository **About → Edit**; README text and `manifest.json` do not change those GitHub settings. See [Releasing](docs/RELEASING.md).

## Features

- **Direct connection:** Home Assistant talks straight to the SMS Gateway Local Server on the Android phone. No Ubuntu proxy, SSH, Magisk, Termux, or cloud account is required.
- **Graphical configuration:** Host/IP, port, username, password, and optional HTTPS via the Home Assistant integration config flow. A reconfigure flow supports updating connection details.
- **Send SMS:** Call `smsgetaweybridge.send_sms` in actions and automations.
- **Receive SMS events:** Polls the gateway's `GET /inbox` endpoint for new incoming messages.
- **Track outgoing status:** Polls `GET /messages` for gateway-reported status changes, including intermediate history where available.
- **Guided admin panel:** sidebar **SMS Bridge** with **Overview**, **Templates & Groups**, **Activity & Logs**, inline help, an SMS composer, template editing and variable-specific forms.
- **Saved templates and groups:** manage and edit up to 50 named groups/templates in the sidebar. Required `$variables` are detected and displayed. The **Send SMS** and **Send saved SMS template** action editors show a live drop-down of saved templates, including each group and required variables. Every saved template also has a dedicated Home Assistant action with individual variable input fields. **Template selection is populated at runtime**: re-open the automation editor after adding or changing templates.
- **Automatic local webhooks:** after you enter Local Server credentials, the integration attempts to register webhook subscriptions on the phone automatically, using the internal Home Assistant HTTPS URL. No URL copying or pasting. If local trusted HTTPS is unavailable or registration fails, polling remains active; the dashboard shows the reason.
- **Origin tracking:** outgoing requests made by HA are recorded by their message ID; other outgoing messages show `external/unknown`, not automatically `Ubuntu`.
- **Diagnostics:** linked HA device entities, capped private activity log and status indicators.
- **Independent clients:** An Ubuntu Server SMS manager can connect to the **same phone** directly; the two systems are independent. Messages sent by either client may appear in shared gateway history.

The project is a **HACS custom integration**, not a Home Assistant Supervisor add-on/App. The new sidebar admin panel provides activity logs and template management; it is **not** a complete conversation archive.

## Requirements

- Home Assistant with support for custom integrations and GUI config flows (the current HA version is recommended).
- [HACS](https://www.hacs.xyz/) to install using the UI (or install manually).
- Android phone with [SMS Gateway for Android](https://github.com/capcom6/android-sms-gateway) installed, configured for **Local Server**, and granted the SMS permissions required by the app.
- Network access **from Home Assistant to the phone's Local Server** (often TCP port `8080`; use the value shown in the app).
- **Local Server** username and password from the phone app. Do not use credentials for any cloud server.

Recommended: reserve the phone's IP in your router's DHCP configuration, or use a stable local hostname. Do **not** expose the Local Server to the public internet.

## Install using HACS (custom repository)

1. In Home Assistant open **HACS** and add the repository `https://github.com/ILoveMyProjects/smsGetaweyBridge` as a **Custom repository** with category **Integration**.
2. Install **smsGetaweyBridge** through HACS and restart Home Assistant when prompted.
3. Go to **Settings → Devices & services → Add integration** and search for **smsGetaweyBridge**.
4. Enter the phone's **Host**, **Port**, **Local Server username**, **Local Server password**, and HTTPS choice.
5. Home Assistant probes `GET /messages` and `GET /inbox`. **It does not send a paid test SMS** during setup.

HACS installs source code from the selected GitHub release/tag (or the default branch). The attached GitHub Release ZIP is an **optional manual-install asset**, not a separate Android APK or prerequisite for HACS. A public GitHub Release may be marked as a pre-release while this integration is in preview.

**Manual install:** copy `custom_components/smsgetaweybridge` from this repository into `<HA_CONFIG>/custom_components/smsgetaweybridge`; restart Home Assistant and add the integration. If installing from the release ZIP, extract its `custom_components` directory into `<HA_CONFIG>/`.

**Change connection details:** on the integration card choose **Reconfigure**. Leave the password blank to keep the currently saved one. No SMS is sent during the connectivity check.

## Send an SMS

In **Developer Tools → Actions**, or in an automation, call:

```yaml
action: smsgetaweybridge.send_sms
data:
  phone_number: "+441234567890"
  message: "Test from Home Assistant"
```

Replace the sample phone number with a number you control. **SMS transmission may incur charges.** If you set up more than one phone, include the appropriate `entry_id` in the action data; when there is only one configured gateway, it is optional.

An API acknowledgment means the gateway **accepted the request**, **not** that the operator delivered the SMS. Delivery reporting depends on the mobile network and device.

## Saved recipient groups and templates (v1.0.0)

From the left sidebar select **SMS Bridge → Templates & Groups**. Create a recipient group using international E.164 phone numbers, e.g. `+441234567890`. Then create a template referencing the group. Use placeholders like `$device` or `${device}` (escaped dollar: `$$`). The admin panel has a visible template list with Edit/Delete controls, and automatically creates text fields for the variables used by the chosen template.

To send a saved template from an HA automation:

```yaml
action: smsgetaweybridge.send_template
data:
  template: server_alert
  variables:
    device: "nas01"
```

The template and recipient group must already exist in the sidebar manager. This action can submit one SMS for each group member, and **partial sending is possible if a later recipient fails**. Check the gateway before retrying. Use unique entry IDs when controlling multiple phones.

## Automatic local HTTPS webhook registration

On installation or reconfiguration, `smsGetaweyBridge` automatically discovers the Home Assistant **internal HTTPS URL** and attempts to register four local webhook subscriptions (`sms:received`, `sms:sent`, `sms:delivered`, `sms:failed`) via the Android Local Server API. No manual URL editing or copying is needed. Only HA-owned webhook IDs are created or refreshed; the Ubuntu manager's webhook subscriptions are untouched. **Polling remains enabled** for resilience.

**Important:** The Android Secure build requires a certificate it trusts. If HA is only accessible via HTTP on the LAN, registration is **not possible** without setting up a valid internal HTTPS endpoint in Home Assistant/network infrastructure. The bridge will report `unavailable_local_https` and keep polling; it will **not** disable Android TLS security, expose a public address or configure your router. It cannot automatically create TLS certificates or change firewall rules. If the registration fails, the panel reports `registration_failed`. **Registered only means the Android API accepted the subscription; actual webhook delivery still needs a live test.**

### Templates from the visual automation editor

Create a recipient group and a template in **SMS Bridge → Templates & Groups**. Example: group `ops`, template key `server_alert`, body `Server $host is $status`.

Then in **Settings → Automations & scenes → Add action**, choose one of:

- **smsGetaweyBridge: Send SMS (direct or saved template)** — choose `server_alert` from the **Saved template** drop-down and enter `host`/`status` in the **Template variables** mapping. The option label lists the group and exact required variables. For a one-off SMS, leave Saved template blank and enter Phone number and Message.
- **smsGetaweyBridge: Send saved SMS template** — the same live drop-down, with group and variable names shown.
- **smsGetaweyBridge: Send SMS: server_alert** — a dedicated action created automatically for this template, with separate `host` and `status` text fields. This is the simplest no-guessing option. After editing a template, re-open the action editor to refresh its fields.

**Never press Run repeatedly after a timeout**: sending may have succeeded at the phone although Home Assistant did not receive its acknowledgement. The integration does not automatically retry paid SMS sending.

Example of the dynamic action (the exact action ID is assigned by Home Assistant from the configured gateway entry):

```yaml
# Use the Home Assistant visual action picker; do not guess the action ID.
action: smsgetaweybridge.send_template
data:
  template: "YOUR_ENTRY_ID::server_alert"
  variables:
    host: "nas"
    status: "offline"
```

If there are multiple configured Android gateways, each drop-down choice identifies its own configuration entry; selecting a template does not route it via Ubuntu.

## Data flow and coexistence with Ubuntu

```text
                  Galaxy S9 / SMS Gateway for Android
                          Local Server (e.g. :8080)
                         /                        \
                        / REST API                 \ REST API
                       v                            v
         Home Assistant / smsGetaweyBridge    Ubuntu Server SMS Manager
                 (independent)                    (independent)
```

Both clients can send via the same phone. Polling `/inbox` and `/messages` does not remove messages; however both clients may see the **same** outgoing events regardless of which system submitted them. Be careful not to create circular automations or unintended duplicate sends.

## Operating limits and reliability

- **Polling interval:** every 30 seconds; HTTPS webhook registration is automatic only when the local HA URL supports valid HTTPS.
- **Pagination:** fetches up to 10,000 inbox results and 10,000 outgoing records per poll. If a category exceeds the safety limit, it reports a synchronization error instead of silently truncating. Exhaustive outgoing scans can burden older phones.
- **Restart/migration:** deduplication checkpoints are saved in HA storage. Initial synchronization and upgrade from v0.1.0 establish a baseline without replaying old messages; the migration cutover may miss messages received during the cutover.
- **Events are at-least-once:** after a crash/restart some events can repeat. Consumers that require one-time behavior must deduplicate by `message_id` or `(message_id, state, changed_at)`.
- **Out-of-order updates:** a late status with an older timestamp may not be detected. Deleted messages cannot be reconstructed from the phone.
- **SMS content:** the upstream API may provide only `contentPreview`, not the entire message. This integration does not support MMS or arbitrary sender IDs such as `HADevMaster` on a regular SIM.
- **Scope:** there is a template/activity admin panel but no full SMS conversation archive or Ubuntu SMS manager in this repository.

## Security

- Keep the gateway Local Server within an isolated LAN/VLAN and allow access only from trusted hosts, including your HA host and (if needed) Ubuntu VM.
- **HTTP Basic Auth does not encrypt credentials or SMS content.** HTTPS should be used with a valid, trusted certificate; this integration does not disable TLS verification or follow cross-host redirects.
- Do not publish phone credentials, SMS contents, one-time verification codes, or diagnostic logs that contain them. Home Assistant automations and the Recorder may retain event payloads.
- For firewall details, credential storage, and privacy, read the [English security guide](docs/SECURITY.md).

## Developers and releases

The project ships with offline Python tests. Release automation runs Python tests, [HACS validation](https://www.hacs.dev/docs/publish/action/), and [Hassfest](https://github.com/home-assistant/actions#hassfest) before publishing a **GitHub Release** when an annotated `vX.Y.Z` tag is pushed. The release includes a manual-install ZIP and SHA-256 checksums. See [RELEASING.md](docs/RELEASING.md) for the exact commands and prerequisites.

Those commands are for developers and GitHub Actions runners only, **not** for phones, HA installations or Ubuntu SMS Manager hosts. See [Developer tests](docs/DEVELOPMENT.md).

CI checks and offline tests do **not** replace a live HA + Android test.

## Links

- [Issues](https://github.com/ILoveMyProjects/smsGetaweyBridge/issues)
- [Releases](https://github.com/ILoveMyProjects/smsGetaweyBridge/releases)
- [Changelog](CHANGELOG.md)
- [Polish docs](docs/README_PL.md)
- [SMS Gateway app](https://github.com/capcom6/android-sms-gateway)
- [SMS Gateway API](https://capcom6.github.io/android-sms-gateway/)

Independent community project; not affiliated with Home Assistant or SMS Gateway for Android.
