# Security and privacy — smsGetaweyBridge

## Network boundary

This Home Assistant integration connects directly to the configured SMS Gateway for Android Local Server. It does not require an external cloud account, an SSH connection, Magisk, or Ubuntu. The configured hostname is not automatically restricted to private IP addresses: **configure a private host**, and enforce the network boundary using LAN/VLAN/firewall rules.

- Do **not** forward the Local Server port to the internet.
- Restrict inbound Local Server connections to the Home Assistant host and any separately trusted clients such as an Ubuntu SMS Manager.
- The Android application's **outgoing** firewall rules and its **incoming** Local Server traffic are different directions. A rule that restricts the Android application's outgoing traffic does not necessarily prevent inbound access.
- Prefer a DHCP reservation or local hostname instead of assuming the phone's DHCP address never changes.
- HTTP Basic Auth alone **does not encrypt** passwords or message contents. Prefer HTTPS with a certificate valid for the host, or use a carefully isolated trusted LAN. TLS verification remains enabled; HTTP redirects are not followed by the integration.

## Credentials and SMS content

Credentials are stored in Home Assistant config entry data; protect Home Assistant storage and backups. Do not put passwords, raw SMS bodies, OTP codes, or tokens into published GitHub issues, debug logs, or dashboards with public access.

The integration fires `smsgetaweybridge_sms_received` events containing sender and message preview. Even if the integration's own deduplication store avoids full message bodies, Home Assistant Recorder, automations, or other integrations may still persist or forward event data. Design an explicit retention and access policy, especially for verification codes.

## Message sending reliability

The integration makes **one POST** per send action and does not retry ambiguous HTTP failures against another endpoint. A timeout can occur *after* the gateway has accepted an SMS. Inspect gateway history before manually retrying a potentially chargeable send.

Reported `Delivered` is an operator/device status, not a read receipt. A `Queued` event is not proof of delivery. Events after polling can be repeated after failure (at-least-once); use message identifiers for deduplication.

## Before production

Validate permissions, outbound SMS to a number you own, inbound SMS detection, status transitions, changing device IP, reboots, and behavior with the intended Home Assistant version and gateway app. Offline tests cannot guarantee the behavior of a particular Android installation.
