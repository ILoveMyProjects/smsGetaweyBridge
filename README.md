# smsGetaweyBridge

[![Tests / HACS / Hassfest](https://github.com/ILoveMyProjects/smsGetaweyBridge/actions/workflows/tests.yml/badge.svg)](https://github.com/ILoveMyProjects/smsGetaweyBridge/actions/workflows/tests.yml)
[![GitHub Releases](https://img.shields.io/github/v/release/ILoveMyProjects/smsGetaweyBridge?include_prereleases)](https://github.com/ILoveMyProjects/smsGetaweyBridge/releases)

**A local-first Home Assistant custom integration for [SMS Gateway for Android](https://github.com/capcom6/android-sms-gateway).** Install it through HACS, configure your Android phone's **Local Server** manually, and use its SMS capabilities from Home Assistant.

**Documentation:** English (this page) · [Polski](docs/README_PL.md) · [Security guide](docs/SECURITY.md) · [Release procedure](docs/RELEASING.md) · [Changelog](CHANGELOG.md)

> **Preview release (v0.1.1).** Offline tests have run, but the integration has **not** been validated end-to-end on a live Home Assistant installation and Android SMS Gateway. Test it with your own device before using it for critical alerts. The GitHub repository and release availability must be checked on GitHub after uploading this project.

## Features

- **Direct connection:** Home Assistant talks straight to the SMS Gateway Local Server on the Android phone. No Ubuntu proxy, SSH, Magisk, Termux, or cloud account is required.
- **Graphical configuration:** Host/IP, port, username, password, and optional HTTPS via the Home Assistant integration config flow. A reconfigure flow supports updating connection details.
- **Send SMS:** Call `smsgetaweybridge.send_sms` in actions and automations.
- **Receive SMS events:** Polls the gateway's `GET /inbox` endpoint for new incoming messages.
- **Track outgoing status:** Polls `GET /messages` for gateway-reported status changes, including intermediate history where available.
- **Diagnostics:** Gateway online indicator and counters for the most recently synchronized inbox/outgoing results.
- **Independent clients:** An Ubuntu Server SMS manager can connect to the **same phone** directly; the two systems are independent. Messages sent by either client may appear in shared gateway history.

The project is a **HACS custom integration**, not a Home Assistant Supervisor add-on/App. There is no built-in full SMS inbox dashboard.

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

## Incoming messages and outgoing status events

The integration fires these Home Assistant events after polling:

| Event type | Useful fields | Meaning |
| --- | --- | --- |
| `smsgetaweybridge_sms_received` | `entry_id`, `message_id`, `sender`, `message`, `received_at` | Newly detected incoming SMS; content may be a preview |
| `smsgetaweybridge_sms_status` | `entry_id`, `message_id`, `state`, `changed_at` | Outgoing gateway state change; not always proof of delivery |
| `smsgetaweybridge_sms_queued` | `entry_id`, `message_id`, `phone_number` | SMS request accepted by the API from Home Assistant |

Example: notify an administrator when an incoming SMS is detected **without displaying its body**:

```yaml
alias: "SMS Gateway - incoming message"
triggers:
  - trigger: event
    event_type: smsgetaweybridge_sms_received
actions:
  - action: persistent_notification.create
    data:
      title: "Incoming SMS"
      message: "SMS received from {{ trigger.event.data.sender }}"
mode: queued
```

Example: react to a reported state change:

```yaml
alias: "SMS Gateway - status"
triggers:
  - trigger: event
    event_type: smsgetaweybridge_sms_status
actions:
  - action: persistent_notification.create
    data:
      title: "SMS status"
      message: "{{ trigger.event.data.message_id }}: {{ trigger.event.data.state }}"
mode: queued
```

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

- **Polling interval:** every 30 seconds; **no inbound webhook server** is required in Home Assistant.
- **Pagination:** fetches up to 10,000 inbox results and 10,000 outgoing records per poll. If a category exceeds the safety limit, it reports a synchronization error instead of silently truncating. Exhaustive outgoing scans can burden older phones.
- **Restart/migration:** deduplication checkpoints are saved in HA storage. Initial synchronization and upgrade from v0.1.0 establish a baseline without replaying old messages; the migration cutover may miss messages received during the cutover.
- **Events are at-least-once:** after a crash/restart some events can repeat. Consumers that require one-time behavior must deduplicate by `message_id` or `(message_id, state, changed_at)`.
- **Out-of-order updates:** a late status with an older timestamp may not be detected. Deleted messages cannot be reconstructed from the phone.
- **SMS content:** the upstream API may provide only `contentPreview`, not the entire message. This integration does not support MMS or arbitrary sender IDs such as `HADevMaster` on a regular SIM.
- **Scope:** there is no dedicated SMS conversations GUI or central Ubuntu SMS manager in this repository.

## Security

- Keep the gateway Local Server within an isolated LAN/VLAN and allow access only from trusted hosts, including your HA host and (if needed) Ubuntu VM.
- **HTTP Basic Auth does not encrypt credentials or SMS content.** HTTPS should be used with a valid, trusted certificate; this integration does not disable TLS verification or follow cross-host redirects.
- Do not publish phone credentials, SMS contents, one-time verification codes, or diagnostic logs that contain them. Home Assistant automations and the Recorder may retain event payloads.
- For firewall details, credential storage, and privacy, read the [English security guide](docs/SECURITY.md).

## Developers and releases

The project ships with offline Python tests. Release automation runs Python tests, [HACS validation](https://www.hacs.dev/docs/publish/action/), and [Hassfest](https://github.com/home-assistant/actions#hassfest) before publishing a **GitHub Release** when an annotated `vX.Y.Z` tag is pushed. The release includes a manual-install ZIP and SHA-256 checksums. See [RELEASING.md](docs/RELEASING.md) for the exact commands and prerequisites.

```bash
python -m pip install aiohttp
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

CI checks and offline tests do **not** replace a live HA + Android test.

## Links

- [Issues](https://github.com/ILoveMyProjects/smsGetaweyBridge/issues)
- [Releases](https://github.com/ILoveMyProjects/smsGetaweyBridge/releases)
- [Changelog](CHANGELOG.md)
- [Polish docs](docs/README_PL.md)
- [SMS Gateway app](https://github.com/capcom6/android-sms-gateway)
- [SMS Gateway API](https://capcom6.github.io/android-sms-gateway/)

Independent community project; not affiliated with Home Assistant or SMS Gateway for Android.
