#!/usr/bin/env python3
"""scopus-cli - a tiny, dependency-free command line for the Elsevier/Scopus API.

Auth: set SCOPUS_API_KEY in the environment (get a key at https://dev.elsevier.com).
Optionally set SCOPUS_INSTTOKEN for institutional entitlements (full text, citation
overview). Stdlib only - no pip install required to run.

Subcommands:
  search    Scopus Search - query the citation database, get DOIs + citation counts
  abstract  Abstract Retrieval - pull one record's abstract + metadata by DOI/EID/Scopus ID
  author    Author Search - find authors by name

Examples:
  scopus search 'TITLE-ABS-KEY("labor share" AND automation)' --count 5
  scopus search '"task-based" automation' --since 2018 --sort -citedby-count --bibtex
  scopus abstract 10.1086/705716
  scopus author 'Acemoglu' --affil MIT
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.elsevier.com/content"


class ScopusError(RuntimeError):
    pass


def _key(cli_key: str | None) -> str:
    key = cli_key or os.environ.get("SCOPUS_API_KEY")
    if not key:
        raise ScopusError(
            "No API key. Set SCOPUS_API_KEY in the environment or pass --api-key. "
            "Get one at https://dev.elsevier.com."
        )
    return key


def _get(path: str, params: dict | None, api_key: str) -> tuple[dict, dict]:
    """GET a Scopus endpoint, return (json_body, response_headers)."""
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"X-ELS-APIKey": api_key, "Accept": "application/json"}
    insttoken = os.environ.get("SCOPUS_INSTTOKEN")
    if insttoken:
        headers["X-ELS-Insttoken"] = insttoken
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode("utf-8"))
            return body, dict(r.headers)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise ScopusError(f"HTTP {e.code} on {path}: {detail}") from None
    except urllib.error.URLError as e:
        raise ScopusError(f"network error on {path}: {e.reason}") from None


def _quota_note(headers: dict) -> str:
    rem = headers.get("X-RateLimit-Remaining")
    lim = headers.get("X-RateLimit-Limit")
    return f"  [quota {rem}/{lim} weekly remaining]" if rem else ""


# ---------------------------------------------------------------- search

def _build_query(args) -> str:
    q = args.query
    # Bare terms (no field operator / parentheses) get wrapped in TITLE-ABS-KEY.
    if not any(op in q for op in ("(", "TITLE", "ABS", "KEY", "AUTH", "AFFIL", "DOI", "PUBYEAR", "SRCTITLE")):
        q = f"TITLE-ABS-KEY({q})"
    if args.since:
        q = f"({q}) AND PUBYEAR > {int(args.since) - 1}"
    return q


def _authors(entry: dict) -> str:
    a = entry.get("dc:creator")
    return a if a else "-"


def _bibtex(entry: dict) -> str:
    raw = (entry.get("dc:creator") or "anon").replace(",", " ").split()
    surname = "".join(c for c in (raw[0] if raw else "anon") if c.isalnum()).lower() or "anon"
    year = (entry.get("prism:coverDate") or "0000")[:4]
    title = entry.get("dc:title") or ""
    first = "".join(c for c in title.split(" ")[0] if c.isalnum()).lower() if title else "x"
    cite = f"{surname}{year}{first}"
    doi = entry.get("prism:doi")
    fields = [
        ("title", title),
        ("author", entry.get("dc:creator") or ""),
        ("journal", entry.get("prism:publicationName") or ""),
        ("year", year),
        ("volume", entry.get("prism:volume") or ""),
        ("doi", doi or ""),
    ]
    lines = [f"@article{{{cite},"]
    lines += [f"  {k} = {{{v}}}," for k, v in fields if v]
    lines.append("}")
    return "\n".join(lines)


def cmd_search(args) -> int:
    api_key = _key(args.api_key)
    query = _build_query(args)
    want = max(1, args.count)
    entries: list[dict] = []
    headers: dict = {}
    start = 0
    total_results = 0
    while len(entries) < want:
        page = min(25, want - len(entries))  # STANDARD view caps at 25/page
        body, headers = _get(
            "/search/scopus",
            {"query": query, "count": page, "start": start, "sort": args.sort, "view": "STANDARD"},
            api_key,
        )
        sr = body.get("search-results", {})
        batch = sr.get("entry", [])
        if not batch or "error" in (batch[0] if batch else {}):
            break
        entries.extend(batch)
        total_results = int(sr.get("opensearch:totalResults", 0))
        start += page
        if start >= total_results:
            break

    if args.json:
        print(json.dumps(entries[:want], indent=2))
        return 0
    if args.bibtex:
        print("\n\n".join(_bibtex(e) for e in entries[:want]))
        return 0

    print(f"query: {query}{_quota_note(headers)}")
    print(f"{min(want, len(entries))} shown of {total_results} total")
    for i, e in enumerate(entries[:want], 1):
        title = (e.get("dc:title") or "?").strip()
        year = (e.get("prism:coverDate") or "")[:4]
        cited = e.get("citedby-count", "0")
        doi = e.get("prism:doi") or "-"
        venue = (e.get("prism:publicationName") or "").strip()
        print(f"\n{i:>2}. {title}")
        print(f"    {_authors(e)} | {year} | {venue}")
        print(f"    cited: {cited} | doi: {doi}")
    return 0


# ---------------------------------------------------------------- abstract

def cmd_abstract(args) -> int:
    api_key = _key(args.api_key)
    ident = args.id.strip()
    if ident.lower().startswith("10."):
        path = f"/abstract/doi/{ident}"
    elif ident.startswith("2-s2.0-"):
        path = f"/abstract/eid/{ident}"
    elif ident.isdigit():
        path = f"/abstract/scopus_id/{ident}"
    else:
        path = f"/abstract/doi/{ident}"
    params = {"view": args.view} if args.view else None
    body, headers = _get(path, params, api_key)
    if args.json:
        print(json.dumps(body, indent=2))
        return 0
    core = body.get("abstracts-retrieval-response", {})
    cc = core.get("coredata", {})
    title = cc.get("dc:title", "?")
    desc = cc.get("dc:description") or "(no abstract returned for this entitlement tier)"
    print(f"{title}")
    print(f"{cc.get('prism:publicationName','')} | {cc.get('prism:coverDate','')[:4]} | "
          f"cited: {cc.get('citedby-count','?')} | doi: {cc.get('prism:doi','-')}")
    print()
    print(desc.strip())
    print(_quota_note(headers).strip())
    return 0


# ---------------------------------------------------------------- author

def cmd_author(args) -> int:
    api_key = _key(args.api_key)
    q = f"AUTHLAST({args.name})"
    if args.affil:
        q += f" AND AFFIL({args.affil})"
    body, headers = _get("/search/author", {"query": q, "count": args.count}, api_key)
    entries = body.get("search-results", {}).get("entry", [])
    if args.json:
        print(json.dumps(entries, indent=2))
        return 0
    print(f"query: {q}{_quota_note(headers)}")
    for e in entries:
        name = e.get("preferred-name", {})
        full = f"{name.get('surname','?')}, {name.get('given-name','')}"
        aid = (e.get("dc:identifier") or "").replace("AUTHOR_ID:", "")
        affil = e.get("affiliation-current", {}).get("affiliation-name", "")
        print(f"- {full} | AU-ID {aid} | docs {e.get('document-count','?')} | {affil}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="scopus", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api-key", help="overrides SCOPUS_API_KEY env")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="Scopus Search")
    s.add_argument("query", help="Scopus query; bare terms are wrapped in TITLE-ABS-KEY()")
    s.add_argument("--count", type=int, default=10, help="number of results (paginates; default 10)")
    s.add_argument("--since", type=int, help="only results from this year onward")
    s.add_argument("--sort", default="-citedby-count", help="sort key (default -citedby-count; e.g. -coverDate)")
    s.add_argument("--bibtex", action="store_true", help="emit BibTeX entries")
    s.add_argument("--json", action="store_true", help="raw JSON")
    s.set_defaults(func=cmd_search)

    a = sub.add_parser("abstract", help="Abstract Retrieval by DOI / EID / Scopus ID")
    a.add_argument("id", help="a DOI (10.x), EID (2-s2.0-...), or numeric Scopus ID")
    a.add_argument("--view", help="FULL or REF (entitlement-gated); omit for default")
    a.add_argument("--json", action="store_true", help="raw JSON")
    a.set_defaults(func=cmd_abstract)

    au = sub.add_parser("author", help="Author Search")
    au.add_argument("name", help="author surname")
    au.add_argument("--affil", help="filter by affiliation name")
    au.add_argument("--count", type=int, default=10)
    au.add_argument("--json", action="store_true")
    au.set_defaults(func=cmd_author)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ScopusError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
