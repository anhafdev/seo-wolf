# Configuration

SEO Wolf reads settings from three places, in this order:

1. Environment variables (prefix `SEOWOLF_`) or a `.env` file in the working folder
2. A YAML crawl file passed with `--config`
3. Command-line flags, which always win

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `SEOWOLF_DATA_DIR` | `~/.seowolf` | Folder for the default SQLite database |
| `SEOWOLF_DATABASE_URL` | SQLite inside the data folder | Any SQLAlchemy async URL, for example `postgresql+asyncpg://wolf:secret@localhost/seowolf` |

Postgres needs the optional extra: `pip install "seowolf[postgres]"`.

## YAML crawl file

```yaml
project: client-shop
crawl:
  start_url: https://shop.example/
  max_urls: 20000
  concurrency: 6
  per_host_delay: 0.5
  exclude_patterns:
    - "/cart"
    - "\\?sort="
  query_policy: strip_listed
  stripped_parameters: ["utm_*", "gclid", "fbclid"]
  custom_headers:
    X-Audit-Token: replace-me
```

A flat file without the `crawl:` key works too.

## Crawl options

| Option | CLI flag | Default | Meaning |
|---|---|---|---|
| `start_url` | argument | required | First page of the crawl |
| `max_urls` | `--max-urls` | 50000 | Maximum pages stored |
| `max_resources` | — | 100000 | Maximum image, script, stylesheet and external checks |
| `max_depth` | `--max-depth` | unlimited | Maximum click depth from the start URL |
| `concurrency` | `--concurrency` | 4 | Parallel requests, 1 to 64 |
| `per_host_concurrency` | — | 4 | Parallel requests to one host |
| `per_host_delay` | `--delay` | 0.25 | Seconds between requests to the same host |
| `timeout_seconds` | `--timeout` | 20 | Request timeout |
| `max_retries` | — | 3 | Retries for 429, 503, timeouts and connection errors |
| `max_redirect_hops` | — | 10 | Redirect hops followed before giving up |
| `respect_robots` | `--ignore-robots` | true | Obey `robots.txt` |
| `user_agent` | `--user-agent` | `SEOWolf/<version> (+repo url)` | Custom User-Agent string |
| `custom_headers` | `--header "Name: value"` | none | Extra request headers |
| `include_patterns` | `--include` | none | Regexes a URL must match to be crawled |
| `exclude_patterns` | `--exclude` | none | Regexes that stop a URL from being crawled |
| `subdomain_policy` | `--all-subdomains` | `same_host` | `same_host` (plus the www twin) or `all_subdomains` |
| `query_policy` | `--query-policy` | `keep` | `keep`, `strip_listed` or `strip_all` |
| `stripped_parameters` | — | tracking parameters | Names or globs removed by `strip_listed` |
| `trailing_slash` | `--trailing-slash` | `keep` | `keep`, `add` or `remove` |
| `follow_nofollow` | `--follow-nofollow` | false | Crawl links marked `rel="nofollow"` |
| `check_resources` | `--no-resources` | true | Check images, scripts and stylesheets |
| `check_external_links` | `--no-external` | true | Check external links |
| `list_mode` | `--list-mode` | false | Audit only the given URLs, no discovery |
| `url_list` | `--url-list FILE` | none | One URL per line |
| `sitemap_urls` | `--sitemap` | none | Extra sitemap or sitemap index URLs |
| `use_robots_sitemaps` | — | true | Read `Sitemap:` lines from `robots.txt` |
| `store_html` | `--store-html` | false | Keep raw HTML for each page |
| `max_html_bytes` | — | 2000000 | Cap for stored HTML per page |
| `allow_private_networks` | `--allow-private-networks` | false | Allow private and loopback targets; CLI only |
