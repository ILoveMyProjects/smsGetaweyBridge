# smsGetaweyBridge v0.1.1 — verification and release audit

Reviewed: 2026-10-17. Based on v0.1.0 archive and audit report. No changes were made to Galaxy S9, Home Assistant, or Ubuntu Server.

## Requirement-by-requirement review

| Issue from v0.1.0 audit | Status | Evidence and limits |
| --- | --- | --- |
| Only first 100 received/outbound messages read | **PASS (offline)** | `api.py`: paginated reads, 250/page, first poll baselines; later `GET /inbox?from=...`, outgoing full pagination; tests `test_pagination_over_100_records`, `test_downtime_over_100_records_not_dropped`, `test_inbox_date_cursor_passed_to_api`. Explicit failure above 10,000 records; no silent truncation. |
| Intermediate state transitions lost | **PASS (offline)** | `coordinator.py`: reads `states` history and emits per-transition events with `changed_at`; tests `test_status_history_replays_intermediate_transitions`, `test_outbound_change_after_restart`. Late history entries with backdated timestamps remain a limitation. |
| HTTP 404/405 automatic SMS route fallback | **PASS (offline)** | `api.py`: exactly one POST to the Local Server's documented `/message`, without retry or fallback; tests for 404, 405, timeout and server errors. |
| Home Assistant configuration and restart tests missing | **PARTIAL** | Mocked tests cover manual configuration, reconfiguration, failed duplicates, service action, restarts and migration; **real HA runtime and end-to-end integration tests have not been run**. |
| GitHub metadata contain placeholders | **BLOCKED on real GitHub owner** | `tools/prepare_github.py --owner REAL_OWNER` fills documentation URL, issue tracker and codeowners. Tested on temporary copy. Original package intentionally keeps placeholders: never invent the account. **Run before public GitHub release**. |
| No reconfigure flow | **PASS (mocked only)** | `config_flow.py` supports changing host, port, username, HTTPS and password without showing existing secret; new translations and config-flow tests. Validate on real HA before declaring stable. |
| IPv6 addresses rejected | **NOT CHANGED (documented)** | GUI accepts hostname and IPv4; literal IPv6 not supported. No expansion of protocol scope. |
| Crash after event dispatch can replay events | **DOCUMENTED, not eliminated** | At-least-once event semantics explicitly documented. Consumers requiring idempotence should deduplicate event IDs. Exactly-once delivery across HA crashes cannot be guaranteed with this storage/event design. |

## Verification executed

- `python -m unittest discover -s tests -q`: **35/35 PASS**.
- `python -m compileall -q custom_components tests tools`: **PASS**.
- Metadata generation checked by running `tools/prepare_github.py --owner ExampleOwner` in temporary copy, verifying URLs and codeowners: **PASS**.
- ZIP integrity and structure: see packaging checks completed at release packaging time.

## Important operational limits

- No automatic installation of Home Assistant components, Termux packages or APKs; no SSH access is used by the integration.
- Client never follows HTTP redirects with Basic authentication, but plain HTTP in LAN does **not** encrypt username/password.
- Incoming SMS checkpoint is based on upstream `createdAt`; newly indexed records with earlier/backdated timestamps may be missed.
- Outgoing status event checkpoint is based on timestamps in `states`; late/backdated status transitions may be missed.
- Full outgoing scanning every 30 seconds can impose load on an old Galaxy S9. Maximum 10,000 per API list per poll; above that limit the update fails visibly.
- Concurrent changes while offset-based pagination is underway are not an atomic snapshot; the following polling cycle may recover records, but it cannot guarantee perfect snapshot consistency.
- Initial setup and one-time upgrade from v0.1.0 intentionally baseline historical messages; events that arrived during the migration may not be emitted.
- `smsgetaweybridge_sms_received` may contain private SMS previews/OTPs in HA events; follow the security guide.
- Never publish the archive unchanged to GitHub: the owner name is unknown, so repository URLs remain placeholders until prepared.
- Live validation with HA and Local Server on the physical phone is required before a stable release can be claimed.
