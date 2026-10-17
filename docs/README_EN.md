# smsGetaweyBridge — HACS custom integration

A custom Home Assistant integration that **directly** connects to SMS Gateway for Android (Local Server). No SSH, Magisk, cloud account, or Ubuntu intermediary.

## Features

- GUI config flow for phone host, port, Local Server username/password and HTTPS option.
- `smsgetaweybridge.send_sms` action to queue an SMS.
- Poll `GET /inbox` and `GET /messages` every 30 seconds to detect incoming messages and status changes.
- Home Assistant events `smsgetaweybridge_sms_received`, `smsgetaweybridge_sms_status`, and `smsgetaweybridge_sms_queued`.
- Three read-only statistics sensors plus an online binary sensor.
- Works alongside an independent Ubuntu SMS Manager connecting to the same phone.

## Installation

1. Upload the entire repository to GitHub.
2. Before publishing, run `python tools/prepare_github.py --owner YOUR_GITHUB_USERNAME` locally (no network traffic). This replaces placeholder URLs and codeowner in `manifest.json`. Verify the URLs and ensure the repository is named `smsGetaweyBridge`. **Do not publish before completing this step.**
3. In HACS add the GitHub repository as a **Custom repository** of type **Integration**.
4. Download the integration, restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → smsGetaweyBridge**.
6. Enter host, port (default 8080), Local Server username and password. Setup tests `/messages` and `/inbox` without sending an SMS.

Alternatively, copy `custom_components/smsgetaweybridge` directly into your Home Assistant configuration directory under `custom_components` and restart HA.

## Reconfigure

Use **Reconfigure** on the integration entry to change the phone IP/host, port or username. Leave password blank to retain the stored one. This checks the read endpoints before applying the change.

## Send an SMS

```yaml
action: smsgetaweybridge.send_sms
data:
  phone_number: "+441234567890"
  message: "Test from Home Assistant"
```

When multiple gateways are configured, set `entry_id` as well.

## Events

- Incoming: `smsgetaweybridge_sms_received` with `message_id`, `sender`, `recipient`, `message` (API preview), `received_at`, `sim_number`, `entry_id`.
- Outbound state transition: `smsgetaweybridge_sms_status` with `message_id`, `state`, `changed_at`, `entry_id`.
- Queued by the HA action: `smsgetaweybridge_sms_queued` with `message_id`, `phone_number`, `entry_id`.

SMS bodies can contain private information, including OTP codes; avoid logging event payloads or forwarding them externally.

## Scope and limitations

Version 0.1.1 is a **preview implementation**, not device-validated. It uses polling, not webhooks (no inbound HTTPS setup needed). The integration paginates inbox messages from a persistent date cursor and scans the outgoing message listing (250 records/page, hard safety ceiling of 10,000 records per list per cycle). If exceeded, polling reports an error instead of silently skipping records. The exhaustive outgoing scan every 30 seconds may be expensive on busy phones. Historic messages are marked as already known on first setup and when migrating data from v0.1.0 (a one-off upgrade cutover may skip messages received during the migration). Intermediate outgoing transitions are reconstructed from the API `states` timeline and emitted with `changed_at`. Events are at-least-once; deduplicate by message ID or `(message_id, state, changed_at)` when required. Late events with backdated timestamps may not be detected. It does not provide a dedicated SMS inbox UI or MMS support. Sending acceptance does not guarantee delivery. For manual configuration and security details see the [Polish guide](INSTALACJA_PL.md) and [security guide](BEZPIECZENSTWO_PL.md).

Local Server over HTTP Basic Auth is **not encrypted**. Use an isolated local network or properly verified HTTPS. Do not forward the Local Server port to the internet. This component does not depend on or manage any Ubuntu server.

## Upstream APIs

- [SMS Gateway app](https://github.com/capcom6/android-sms-gateway)
- [OpenAPI documentation](https://capcom6.github.io/android-sms-gateway/)
- [HACS integration repository requirements](https://www.hacs.dev/docs/publish/integration/)
