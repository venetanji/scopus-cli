# scopus-cli

A tiny, **dependency-free** command line for the [Elsevier / Scopus API](https://dev.elsevier.com).
Search the citation database, pull abstracts, and emit BibTeX — straight from the terminal,
stdlib only, no `pip install` required to run.

## Auth

Get a key at <https://dev.elsevier.com> and export it:

```bash
export SCOPUS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# optional — unlocks full-text / citation-overview if your institution provides one:
export SCOPUS_INSTTOKEN=...
```

API keys are tied to an account; **never commit one**. This repo's `.gitignore` excludes
`.env` and `*.key`.

## Run

No install needed:

```bash
python3 scopus_cli/cli.py search 'TITLE-ABS-KEY("labor share" AND automation)' --count 5
```

Or install it as a `scopus` command:

```bash
pip install -e .        # or: uv tool install .
scopus search '"task-based" automation' --since 2018 --bibtex
```

## Commands

### `search`
```bash
scopus search '<query>' [--count N] [--since YEAR] [--sort -citedby-count] [--bibtex] [--json]
```
- Bare terms are wrapped in `TITLE-ABS-KEY(...)`; pass a full Scopus query to take control.
- `--since 2018` adds `PUBYEAR > 2017`.
- Paginates automatically (the STANDARD view returns 25/page).
- `--bibtex` emits ready-to-paste `@article` entries; `--json` dumps raw entries.

### `abstract`
```bash
scopus abstract 10.1086/705716          # by DOI
scopus abstract 2-s2.0-85049...          # by EID
scopus abstract 85049012345 --json       # by Scopus ID
```
Prints title, venue, year, citation count, DOI, and the abstract.

### `author`
```bash
scopus author Acemoglu --affil MIT
```
Finds authors by surname (+ optional affiliation) and returns their AU-ID + document count.

## Query syntax (cheat sheet)

| Field | Example |
|---|---|
| Title/abstract/keywords | `TITLE-ABS-KEY("comparative advantage")` |
| Exact title | `TITLE(automation)` |
| Author | `AUTH(Acemoglu)` / `AU-ID(7003520724)` |
| Affiliation | `AFFIL(MIT)` |
| Year | `PUBYEAR > 2015` |
| Source | `SRCTITLE("American Economic Review")` |
| DOI | `DOI(10.1086/705716)` |
| Boolean | `... AND ... OR ... AND NOT ...` |

Sort with `--sort -citedby-count` (most cited) or `--sort -coverDate` (newest).

## Entitlements (what a plain API key gets you)

| Endpoint | Plain key | Notes |
|---|---|---|
| Scopus **Search** | ✅ | 20,000 requests / week, ~9 req/s |
| **Abstract Retrieval** (metadata + citation count) | ✅ | abstract *text* needs `SCOPUS_INSTTOKEN` |
| **Author Search** (`/search/author`) | ❌ | 401 without `SCOPUS_INSTTOKEN` |
| Abstract `--view FULL` / `REF` | ⚠️ | usually needs `SCOPUS_INSTTOKEN` |
| Citation Count / Citation Overview | ❌ | needs institutional entitlement (but `citedby-count` is already in Search results) |
| ScienceDirect full text | ❌ | needs institutional token + subscription |

## License

MIT.
