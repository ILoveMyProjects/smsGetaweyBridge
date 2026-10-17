# Changelog

## 0.2.1 — Preview: HACS/Hassfest CI compatibility fixes

- Declare the config-entry-only `CONFIG_SCHEMA` required by Hassfest for `async_setup` integrations.
- Order manifest keys correctly (`domain`, `name`, then alphabetical), and bump the integration version for HACS updates.
- Bundle original local brand icons under `custom_components/smsgetaweybridge/brand/` to satisfy HACS brand validation and provide a device/integration icon.
- Update GitHub Actions runtime dependencies (`actions/checkout@v5` and `actions/setup-python@v6`) to avoid Node.js 20 deprecation notices.
- Add offline regression checks for manifest ordering, schema declaration, brand assets and workflow action versions.
- Document mandatory repository-side GitHub description/topics, which cannot be set by an integration ZIP.

**Validation note:** HACS/Hassfest must still be run in GitHub Actions; this update addresses the specific log findings but does not claim live CI validation.

## 0.2.0 — Preview: Admin panel, templates and activity

- Add an administrator-only Home Assistant sidebar panel with **Overview**, **Templates** and **Logs** tabs.
- Add named recipient groups and message templates stored persistently in Home Assistant.
- Add `smsgetaweybridge.send_template` action, which substitutes named `$variables` safely and sends to a saved group.
- Track IDs of requests sent from Home Assistant, labeling all other observed sends as `external/unknown` rather than assuming Ubuntu origin.
- Add device registry metadata for the online, inbox count, outgoing count and status entities.
- Add capped privacy-conscious activity log (no SMS contents or full destination numbers).
- Add opt-in, local-only Home Assistant webhooks requiring an internal HTTPS origin trusted by the Galaxy phone; polling remains enabled.
- Keep both HA and Ubuntu as independent clients of the phone's Local Server. No software installed on the phone.

**Preview restrictions:** Not tested end-to-end against a running Home Assistant/Galaxy S9. Outgoing multi-recipient group sends may partially complete before an error. No automatic retries. Webhook configuration can require local TLS certificate and special network setup. Background periodic polling of large outgoing histories continues.

## 0.1.1 — Preview, audit fixes

- Paginated inbox reads from a persisted timestamp cursor, and paginated full outgoing scans (250 per page, explicit 10,000 record ceiling with error on overflow).
- Persistent UTC timestamp checkpoints and boundary IDs; no replay after ordinary restarts; safe migration of v0.1.0 stored data.
- Reconstruct intermediate status transitions from upstream `states` timestamp map, with `changed_at` event field.
- Never retry paid SMS POST to another endpoint when the first returns HTTP 404/405; use documented Local Server `/message` only.
- GUI reconfigure for Local Server IP/port/user/password, without showing saved password.
- Expanded regression coverage for paging, downtime, reboots, migration and config flow.
- `tools/prepare_github.py` fills project-owned manifest links and codeowner when the real GitHub owner is known. This must be run before publication.

### Known limits

- No end-to-end test against a running Home Assistant or Galaxy S9; only offline mocks and static checks.
- Exhaustive 30-second polling is heavier on large message stores; over 10,000 records per list yields an explicit update error.
- Event delivery is at-least-once, not exactly-once; late, backdated data and non-snapshot API pagination are limitations.

## 0.1.0 — Preview

- First HACS custom integration package (`smsGetaweyBridge`).
- Manual Local Server configuration via Home Assistant GUI.
- Outgoing SMS action with non-retrying POST and API-path compatibility fallback.
- Polling of incoming SMS and outgoing message states at 30-second intervals.
- Home Assistant events, basic diagnostic entities and persistent ID/state deduplication.
- Polish and English documentation, offline unit tests and GitHub Actions checks.

Not yet end-to-end tested on Home Assistant with a live SMS Gateway device. See README limitations.
