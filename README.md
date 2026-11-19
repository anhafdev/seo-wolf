<div align="center">

<img src="assets/seo-wolf-header.svg" alt="SEO Wolf — self-hosted SEO crawler and site auditor" width="100%">

**Self-hosted SEO crawler and site auditor. Unlimited URLs, saved crawls, every advanced feature free.**

[![CI](https://github.com/anhafdev/seo-wolf/actions/workflows/ci.yml/badge.svg)](https://github.com/anhafdev/seo-wolf/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-2F6BFF)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-E5383B)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-8A93A6)](CHANGELOG.md)

[Quick start](#quick-start) · [What works today](#what-works-today) · [Roadmap](#roadmap) · [Configuration](docs/configuration.md) · [Architecture](docs/architecture.md)

</div>

---

## Why SEO Wolf

The free tier of most desktop crawlers stops at 500 URLs, forgets every crawl the moment you close it, and locks JavaScript rendering, crawl comparison, scheduling and custom extraction behind a yearly licence. Freelancers and small agencies end up paying per seat just to audit their own clients' sites.

SEO Wolf is a deterministic, offline-first crawler you run on your own laptop or VPS. No URL cap, no seat licence, no data sent to anyone. Every crawl is stored, so you can come back to it, compare it, and report on it.

## What works today

Version `0.1.0` ships the crawler foundation:

| Area | Included now |
|---|---|
| Crawling | Async worker pool, per-host politeness, `Crawl-delay`, HTTP 429/503 + `Retry-After` backoff |
| Seeds | Start URL, XML sitemap and sitemap index (gzip), plain-text sitemaps, URL list file, list mode |
| Redirects | Tracked hop by hop (max 10), loops detected, every hop stored |
| Robots | RFC 9309 matching: wildcards, `$` anchors, longest match, agent groups, sitemap discovery |
| Scope | Include/exclude regex, max depth, max URLs, subdomain policy, query-string policy, trailing slash policy |
| Checks | Status of every image, script, stylesheet and external link (HEAD with ranged-GET fallback) |
| Page data | Title, meta description, H1, canonical, meta robots, `X-Robots-Tag`, lang, word count, text ratio, indexability reason |
| Links | Every link with anchor text, rel, nofollow flag and position (nav, header, footer, aside, content) |
| Storage | SQLite (WAL) by default, Postgres-ready schema, Alembic migrations, saved crawls forever |
| Safety | SSRF guard on every connection, honest User-Agent, robots respected by default |
| Resume | Pause with Ctrl+C, continue later with `seowolf crawl resume <id>`, crash-safe frontier |

## Quick start

```bash
git clone https://github.com/anhafdev/seo-wolf.git
cd seo-wolf
python -m pip install -e ".[dev]"

seowolf crawl start https://your-site.example/
seowolf crawl list
seowolf crawl summary 1
```

Press **Ctrl+C** once during a crawl to pause cleanly. Resume with:

```bash
seowolf crawl resume 1
```

Crawls are stored in `~/.seowolf/seowolf.db`. Set `SEOWOLF_DATA_DIR` or `SEOWOLF_DATABASE_URL` to change that.

<details>
<summary><b>More crawl examples</b></summary>

```bash
seowolf crawl start https://shop.example/ --max-urls 5000 --exclude "/cart" --exclude "\?sort="
seowolf crawl start https://example.com/ --all-subdomains --query-policy strip_listed
seowolf crawl start https://example.com/ --list-mode --url-list urls.txt
seowolf crawl start https://example.com/ --list-mode --sitemap https://example.com/sitemap.xml
seowolf crawl start --config wolf.yaml
```

</details>

## How it compares

| Tool type | What it is | Gap SEO Wolf fills |
|---|---|---|
| Paid desktop crawlers (licence about £199–239 a year) | Free tier capped at 500 URLs, no saved crawls, advanced configuration locked | Unlimited URLs, saved crawls, every advanced feature free |
| python-seo-analyzer | Older basic Python crawler with a single-page style report | Modern async crawler, rule engine, dashboard, history |
| SEOnaut (Go) | Self-hosted dashboard crawler | Python ecosystem, JS rendering, AI-search audit, Search Console data, MCP, CI action |
| Node CLI auditors | Rule engine, command line only | Persistent web dashboard, crawl diff, scheduling, alerts |
| AI-agent SEO plugins | Need a language model to run and send page data to it | Deterministic engine, fully offline, AI optional and bring-your-own-key |

SEO Wolf is not affiliated with any commercial SEO vendor.

**Plain truth about data.** Backlink indexes and keyword search-volume databases need web-scale data that no self-hosted tool can produce for free. SEO Wolf covers this with first-party data instead: Google Search Console for your real queries, clicks, impressions and positions, and Bing Webmaster Tools for backlinks to your own site. An optional bring-your-own-key adapter for a paid data API is planned for people who need more.

## Who this is for

- Freelancers who audit client sites and are tired of the 500-URL wall
- Small agencies that want white-label reports without per-seat licences
- Developers who want SEO checks in CI before a release goes live
- Anyone who wants their crawl data on their own machine

## Crawling ethics

SEO Wolf is an audit tool for sites you own or are authorised to audit.

- `robots.txt` is respected by default. `--ignore-robots` prints a warning and is meant for your own sites.
- Polite defaults: 4 concurrent requests, 0.25 s between requests per host, `Crawl-delay` and `Retry-After` honoured.
- Honest User-Agent: `SEOWolf/0.1.0 (+https://github.com/anhafdev/seo-wolf)`. No fingerprint spoofing, no CAPTCHA solving, no anti-bot bypass.
- Private, loopback, link-local, CGNAT and cloud-metadata addresses are blocked at connection time, including after redirects and DNS rebinding. Only the CLI flag `--allow-private-networks` lifts this.

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation: crawler core, storage, robots, sitemaps, SSRF guard, CLI | ✅ Done |
| 2 | Deep parsing and rule engine, first rule categories | Next |
| 3 | Full catalogue of 200+ rules, health score, generated `docs/rules.md` | Planned |
| 4 | Link graph, internal PageRank, duplicates, canonical and hreflang analysis, crawl diff, segments, custom extraction | Planned |
| 5 | JavaScript rendering with Playwright, raw-vs-rendered diff, authenticated crawling, accessibility checks | Planned |
| 6 | GEO / AEO audit: AI crawler access, render dependency, `llms.txt`, answerability, entity signals | Planned |
| 7 | Exports: CSV, XLSX, JSON, HTML and PDF reports, white-label branding | Planned |
| 8 | REST API and web dashboard | Planned |
| 9 | Search Console, GA4, Bing Webmaster, IndexNow, PageSpeed Insights, scheduling and alerts | Planned |
| 10 | MCP server, GitHub Action, Docker images, release | Planned |

<details>
<summary><b>Development</b></summary>

```bash
python -m pip install -e ".[dev]"
ruff check . && ruff format --check .
python -m pytest
```

House rules, enforced by `tests/test_code_style.py`:

- No comments and no docstrings. Names and structure explain the code.
- Every Python file stays at or under 200 lines.
- Plain, readable English names.
- Full type hints, Python 3.11+.
- Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

</details>

---

<div align="center">

**ENGINEERED BY ANHAF**

[anhaf.dev](https://anhaf.dev) · [Telegram @anhafxd](https://t.me/anhafxd) · [GitHub @anhafdev](https://github.com/anhafdev)

<sub>every system leaves a signature · MIT licensed · © 2026 F. ANHAF DEV</sub>

</div>
