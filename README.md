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

## Manual API smoke test

After merging the workflow into `main`, open **Actions → Scopus API smoke test →
Run workflow**, select `main`, and run it. The job uses `SCOPUS_API_KEY` from the
existing GitHub environment named `search`. It never runs on pushes or pull requests.

The probe uses the CLI's existing request/auth/JSON code for one fixed scholarly
search, capped at five results, then one abstract retrieval using an identifier
actually returned by that search. It does not paginate, retry, or follow redirects.
Each response is capped at 1 MiB; requests have a 10-second socket timeout and a
25-second shared time budget. A 35-second process deadline (plus at most 5 seconds
to terminate) and a two-minute job timeout bound slow or stalled responses.

Logs contain only a fixed JSON summary of boolean success/presence flags, numeric
HTTP statuses, and the returned result count. Status `0` means no HTTP response was
received. No keys, queries, identifiers, titles, abstracts, response bodies, or raw
error messages are printed; no artifacts are uploaded.

- `search_metadata_success: true` confirms a usable search response.
- `abstract_metadata_success: true` with `abstract_present: false` confirms metadata
  retrieval without abstract text. Entitlement can affect this; the flag alone
  does not establish why text is absent.
- `abstract_access_denied: true` records HTTP 401/403 for abstract retrieval and
  fails the probe, while preserving the separate search success flag.
- A genuinely empty search succeeds with `abstract_attempted: false`. Results
  without a usable identifier, malformed responses, and other request failures
  fail the probe without printing remote content.

Run the network-mocked tests locally without a key:

```bash
python3 -m unittest discover -s tests -v
```
