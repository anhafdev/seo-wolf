# Security policy

## Reporting a vulnerability

Email **founder@anhaf.dev** with the subject `SEO Wolf security`. Please include steps to reproduce, the affected version and the impact you see. Do not open a public issue for security problems.

You will get a reply within 5 working days. Fixes are released as soon as they are ready, and reporters are credited unless they ask not to be.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |

## Built-in protections

- **SSRF guard.** Every outgoing connection resolves its host and is refused if any address is private, loopback, link-local, CGNAT, multicast, reserved, IPv4-mapped private, NAT64-embedded private or a cloud metadata address. The check runs at connection time, so redirects and DNS rebinding are covered. Only the CLI flag `--allow-private-networks` lifts it.
- **XML safety.** Sitemaps with `DOCTYPE` or `ENTITY` declarations are refused, and gzip sitemaps are inflated with a hard 50 MB limit.
- **Bounded downloads.** Page bodies, robots files and stored HTML all have size caps.
- **No proxy surprises.** The crawler ignores proxy environment variables so the guard always sees the real destination.

## Out of scope

Reports that rely on the user deliberately passing `--allow-private-networks` or `--ignore-robots` against their own infrastructure.
