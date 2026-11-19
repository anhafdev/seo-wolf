# Changelog

All notable changes to SEO Wolf are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- README redesigned with the hexagon wolf logo, a recorded crawl demo, a feature comparison matrix, FAQ and a one-line pipx install
- CI actions updated to checkout v7 and setup-python v7

## [0.1.0] - 2026-11-20

### Added

- Async crawler with a database-backed frontier, pause with Ctrl+C and `seowolf crawl resume`
- Per-host politeness, `Crawl-delay`, HTTP 429/503 and `Retry-After` backoff
- RFC 9309 `robots.txt` matching with wildcard, end anchor, longest match and agent groups
- XML sitemap, sitemap index, gzip and plain-text sitemap support with size and entity protection
- Hop-by-hop redirect tracking with loop and chain detection
- Status checks for images, scripts, stylesheets and external links
- Page parsing for title, meta description, H1, canonical, meta robots, `X-Robots-Tag`, lang, word count and links with position
- Indexability reason for every page
- SSRF guard at connection time for private, loopback, link-local, CGNAT, multicast and metadata addresses
- SQLite (WAL) storage with a Postgres-ready schema and Alembic migrations
- `seowolf crawl start | resume | list | summary` and `seowolf project list`
