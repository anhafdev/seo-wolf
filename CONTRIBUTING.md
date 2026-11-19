# Contributing to SEO Wolf

Thanks for helping. Issues and pull requests are welcome.

## Set up

```bash
git clone https://github.com/anhafdev/seo-wolf.git
cd seo-wolf
python -m pip install -e ".[dev]"
python -m pytest
```

## House rules

These are checked automatically by `tests/test_code_style.py` and `ruff`.

1. No comments and no docstrings. Let names and structure explain the code.
2. Every Python file stays at or under 200 lines. Split into more modules instead.
3. Plain, readable English names: `fetch_page`, `broken_links`, `pages_missing_title`.
4. Full type hints, Python 3.11 or newer.
5. Complete code only. No placeholders or stub bodies.
6. `ruff check .` and `ruff format --check .` must pass.
7. Every Python module carries the project signature line `__author__ = "@anhafxd"`.

## Tests

- New behaviour needs a test. Crawl behaviour is tested against the local fixture site in `tests/fixture_site`.
- Never point tests at real websites. Use the fixture server or `respx`.

## Commits and pull requests

- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- No trailers in commit messages.
- Keep pull requests focused on one change and describe how you tested it.

## Ethics

SEO Wolf is for auditing sites you own or are authorised to audit. Contributions that add fingerprint spoofing, CAPTCHA solving or any anti-bot bypass will not be accepted.
