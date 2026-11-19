<div align="center">

<img src="assets/seo-wolf-logo.svg" alt="SEO Wolf logo" width="128">

<h1>SEO Wolf · Self-Hosted SEO Crawler &amp; Site Audit Tool</h1>

<p><b>Unlimited URLs. Saved crawls. Every advanced feature free.</b><br>
Audit any site you own from your laptop or VPS. Your crawl data never leaves your machine.</p>

[![CI](https://github.com/anhafdev/seo-wolf/actions/workflows/ci.yml/badge.svg)](https://github.com/anhafdev/seo-wolf/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/anhafdev/seo-wolf?color=2F6BFF)](https://github.com/anhafdev/seo-wolf/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-2F6BFF)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-E5383B)](LICENSE)

<a href="#quick-start"><img src="https://img.shields.io/badge/Get%20started-in%2060%20seconds-2F6BFF?style=for-the-badge" alt="Get started in 60 seconds"></a>

[Quick start](#quick-start) · [Features](#what-you-get-today) · [Compare](#how-it-compares) · [Roadmap](#roadmap) · [FAQ](#faq) · [Docs](docs/configuration.md)

</div>

<p align="center">
  <img src="assets/demo-crawl.svg" alt="Terminal output of an SEO Wolf crawl showing 13 pages, redirect chains, status codes, broken internal links and a broken image" width="880">
</p>
<p align="center"><sub>Real output from crawling the test site that ships with the repo. It runs on your own machine, which is why the demo passes <code>--allow-private-networks</code>.</sub></p>

---

## Why SEO Wolf

The free tier of most desktop crawlers stops at 500 URLs, forgets your crawl when you close it, and keeps JavaScript rendering, crawl comparison, scheduling and custom extraction behind a yearly per-user licence. Freelancers and small agencies pay per seat just to audit their own clients' sites.

SEO Wolf is a deterministic, offline-first crawler that runs on your own hardware. No URL cap, no seat licence, no telemetry. Every crawl is saved, so you can come back to it, compare it and report on it.

## Quick start

Needs Python 3.11 or newer on Windows, macOS or Linux.

```bash
pipx install git+https://github.com/anhafdev/seo-wolf.git
seowolf crawl start https://your-site.example/
```

No pipx? `pip install git+https://github.com/anhafdev/seo-wolf.git` works too.

```bash
seowolf crawl list
seowolf crawl summary 1
seowolf crawl resume 1
```

Press **Ctrl+C** once to pause a crawl cleanly. Crawls live in `~/.seowolf/seowolf.db`; set `SEOWOLF_DATA_DIR` or `SEOWOLF_DATABASE_URL` to move them.

<details>
<summary><b>More examples</b></summary>

```bash
seowolf crawl start https://shop.example/ --max-urls 5000 --exclude "/cart" --exclude "\?sort="
seowolf crawl start https://example.com/ --all-subdomains --query-policy strip_listed
seowolf crawl start https://example.com/ --list-mode --url-list urls.txt
seowolf crawl start https://example.com/ --list-mode --sitemap https://example.com/sitemap.xml
seowolf crawl start --config wolf.yaml
```

Every option is listed in [docs/configuration.md](docs/configuration.md).

</details>

## What you get today

| Area | Included in v0.1 |
|---|---|
| Crawling | Async worker pool, per-host politeness, `Crawl-delay`, HTTP 429/503 and `Retry-After` backoff |
| Seeds | Start URL, XML sitemap and sitemap index (gzip), plain-text sitemaps, URL list file, list mode |
| Redirects | Followed hop by hop (max 10), loops detected, every hop stored |
| Robots | RFC 9309 matching: wildcards, `$` anchors, longest match, agent groups, sitemap discovery |
| Scope | Include/exclude regex, max depth, max URLs, subdomain, query-string and trailing-slash policies |
| Checks | Status of every image, script, stylesheet and external link (HEAD with ranged-GET fallback) |
| Page data | Title, meta description, H1, canonical, meta robots, `X-Robots-Tag`, lang, word count, text ratio, indexability reason |
| Links | Every link with anchor text, rel, nofollow flag and position (nav, header, footer, aside, content) |
| Storage | SQLite (WAL) by default, Postgres-ready schema, Alembic migrations, saved crawls forever |
| Safety | SSRF guard on every connection, honest User-Agent, robots respected by default |
| Resume | Pause with Ctrl+C, continue with `seowolf crawl resume <id>`, crash-safe frontier |

## How it compares

| | Typical desktop crawler, free tier | Same crawler, paid licence | SEO Wolf |
|---|:---:|:---:|:---:|
| URL limit | 500 | Unlimited | **Unlimited** ✅ |
| Saved crawls | ❌ | ✅ | ✅ |
| Runs locally, data stays with you | ✅ | ✅ | ✅ |
| Crawl comparison | ❌ | ✅ | 🔜 Phase 4 |
| Custom extraction and segments | ❌ | ✅ | 🔜 Phase 4 |
| JavaScript rendering | ❌ | ✅ | 🔜 Phase 5 |
| Search Console and PageSpeed data | ❌ | ✅ | 🔜 Phase 9 |
| Scheduled crawls | ❌ | ✅ | 🔜 Phase 9 |
| Open source, read and change the code | ❌ | ❌ | ✅ |
| Price | Free | about £199 per user a year | **Free, MIT** ✅ |

✅ works today · 🔜 on the roadmap

<details>
<summary><b>Compared with other open-source tools</b></summary>

| Tool | What it is | What SEO Wolf adds |
|---|---|---|
| python-seo-analyzer | Older basic Python crawler with a single-page style report | Modern async crawler and saved history today; rule engine and dashboard planned |
| SEOnaut (Go) | Self-hosted dashboard crawler | Python ecosystem today; JS rendering, AI-search audit, Search Console data, MCP and CI action planned |
| Node CLI auditors | Rule engine, command line only | Persistent storage and resume today; dashboard, crawl diff, scheduling and alerts planned |
| AI-agent SEO plugins | Need a language model and send page data to it | Deterministic and fully offline; AI stays optional and bring-your-own-key |

</details>

SEO Wolf is not affiliated with any commercial SEO vendor.

**Plain truth about data.** Backlink indexes and keyword search-volume databases need web-scale data that no self-hosted tool can produce for free. SEO Wolf will cover this with first-party data instead: Google Search Console for your real queries, clicks, impressions and positions, and Bing Webmaster Tools for backlinks to your own site, plus an optional bring-your-own-key adapter for a paid data API.

## Who this is for

- Freelancers who audit client sites and keep hitting the 500-URL wall
- Small agencies that want white-label reports without per-seat licences
- Developers who want SEO checks in CI before a release goes live
- Anyone who wants their crawl data on their own machine

## Crawling ethics and safety

SEO Wolf is an audit tool for sites you own or are authorised to audit.

- `robots.txt` is respected by default. `--ignore-robots` prints a warning and is meant for your own sites.
- Polite defaults: 4 concurrent requests, 0.25 s between requests to one host, `Crawl-delay` and `Retry-After` honoured.
- Honest User-Agent: `SEOWolf/0.1.0 (+https://github.com/anhafdev/seo-wolf)`. No fingerprint spoofing, no CAPTCHA solving, no anti-bot bypass.
- Private, loopback, link-local, CGNAT and cloud-metadata addresses are refused at connection time, including after redirects and DNS rebinding. Only the CLI flag `--allow-private-networks` lifts this.

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 1 | Crawler core, storage, robots, sitemaps, SSRF guard, CLI | ✅ Done |
| 2 | Deep parsing and rule engine, first rule categories | 🚧 Next |
| 3 | Full catalogue of 200+ rules, health score, generated `docs/rules.md` | Planned |
| 4 | Link graph, internal PageRank, duplicates, canonical and hreflang analysis, crawl diff, segments, custom extraction | Planned |
| 5 | JavaScript rendering, raw-vs-rendered diff, authenticated crawling, accessibility checks | Planned |
| 6 | GEO / AEO audit: AI crawler access, render dependency, `llms.txt`, answerability, entity signals | Planned |
| 7 | CSV, XLSX, JSON, HTML and PDF reports with white-label branding | Planned |
| 8 | REST API and web dashboard | Planned |
| 9 | Search Console, GA4, Bing Webmaster, IndexNow, PageSpeed Insights, scheduling and alerts | Planned |
| 10 | MCP server, GitHub Action, Docker images, PyPI release | Planned |

## FAQ

<details>
<summary><b>Does SEO Wolf send my data anywhere?</b></summary>

No. It talks only to the site you crawl. There is no telemetry and no account. Future integrations such as Search Console use your own credentials and stay off until you set them up.

</details>

<details>
<summary><b>Can I crawl any website with it?</b></summary>

Use it on sites you own or have permission to audit. It respects `robots.txt` by default, identifies itself honestly and slows down when a server asks it to.

</details>

<details>
<summary><b>How big can a crawl get?</b></summary>

The design target is 50,000 URLs on an 8 GB laptop with SQLite and 250,000 URLs with Postgres on a small VPS. Published benchmarks will follow once the rule engine lands.

</details>

<details>
<summary><b>Why is there no backlink or keyword volume data?</b></summary>

That data needs a web-scale index. SEO Wolf focuses on what it can measure honestly: your site, plus first-party data from Search Console and Bing Webmaster Tools.

</details>

<details>
<summary><b>Can I use Postgres instead of SQLite?</b></summary>

Yes. Install the extra with `pip install "seowolf[postgres] @ git+https://github.com/anhafdev/seo-wolf.git"` and set `SEOWOLF_DATABASE_URL=postgresql+asyncpg://user:password@host/seowolf`.

</details>

<details>
<summary><b>Development and house rules</b></summary>

```bash
git clone https://github.com/anhafdev/seo-wolf.git
cd seo-wolf
python -m pip install -e ".[dev]"
ruff check . && ruff format --check .
python -m pytest
```

Enforced by `tests/test_code_style.py`: no comments or docstrings, every Python file at or under 200 lines, plain English names, full type hints, conventional commits. See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [docs/architecture.md](docs/architecture.md).

</details>

---

<div align="center">

If SEO Wolf saves you a licence fee, a ⭐ helps other freelancers find it.

<br>

<img src="assets/seo-wolf-logo.svg" alt="" width="40">

**ENGINEERED BY ANHAF**

[anhaf.dev](https://anhaf.dev) · [Telegram @anhafxd](https://t.me/anhafxd) · [GitHub @anhafdev](https://github.com/anhafdev)

<sub>every system leaves a signature · MIT licensed · © 2026 F. ANHAF DEV</sub>

</div>
