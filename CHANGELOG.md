# Changelog

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
