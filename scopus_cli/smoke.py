"""Manual, bounded API probe. Emit only fixed scalar fields, never API content."""
import json
import re
import time
import urllib.error
import urllib.request

from . import cli

QUERY = 'TITLE-ABS-KEY("photosynthesis")'
MAX_RESULTS = 5
MAX_REQUESTS = 2
MAX_RESPONSE_BYTES = 1024 * 1024
REQUEST_TIMEOUT = 10
PROBE_TIMEOUT = 25


class ProbeFailure(Exception):
    """Intentionally carries no remote error details."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an API-key header to a redirect destination.
        return None


class BoundedResponse:
    def __init__(self, response, deadline):
        self.response = response
        self.headers = response.headers
        self.deadline = deadline

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.response.close()

    def read(self):
        if time.monotonic() >= self.deadline:
            raise ProbeFailure()
        content = self.response.read(MAX_RESPONSE_BYTES + 1)
        if len(content) > MAX_RESPONSE_BYTES or time.monotonic() >= self.deadline:
            raise ProbeFailure()
        return content


class BoundedTransport:
    """Transport injected into the CLI's existing request/auth/JSON path."""
    def __init__(self):
        self.opener = urllib.request.build_opener(NoRedirect())
        self.requests = 0
        self.status = 0
        self.deadline = time.monotonic() + PROBE_TIMEOUT

    def __call__(self, request, *, timeout):
        self.status = 0
        remaining = self.deadline - time.monotonic()
        if self.requests >= MAX_REQUESTS or remaining <= 0:
            raise ProbeFailure()
        self.requests += 1
        try:
            response = self.opener.open(request, timeout=min(timeout, REQUEST_TIMEOUT, remaining))
        except urllib.error.HTTPError as error:
            # Do not read the response body or let CLI error formatting expose it.
            self.status = error.code if type(error.code) is int else 0
            error.close()
            raise ProbeFailure() from None
        except Exception:
            raise ProbeFailure() from None
        self.status = response.status if type(response.status) is int else 0
        return BoundedResponse(response, self.deadline)


def _fetch(summary, phase, path, params, api_key, transport):
    try:
        body, _ = cli._get(path, params, api_key, open_url=transport)
        return body
    finally:
        summary[phase + "_status"] = transport.status
        summary[phase + "_http_success"] = 200 <= transport.status < 300
        if phase == "abstract":
            summary["abstract_access_denied"] = transport.status in (401, 403)


def _probe(summary):
    api_key = cli._key(None)
    transport = BoundedTransport()
    body = _fetch(summary, "search", "/search/scopus", {
        "query": QUERY, "count": MAX_RESULTS, "start": 0,
        "sort": "-citedby-count", "view": "STANDARD",
    }, api_key, transport)
    results = body.get("search-results") if isinstance(body, dict) else None
    if not isinstance(results, dict):
        raise ProbeFailure()
    entries = results.get("entry", [])
    if not isinstance(entries, list) or len(entries) > MAX_RESULTS:
        raise ProbeFailure()
    if any(not isinstance(entry, dict) for entry in entries):
        raise ProbeFailure()
    empty = str(results.get("opensearch:totalResults")) == "0"
    if empty and (not entries or (len(entries) == 1 and "error" in entries[0])):
        entries = []
    elif not entries or any("error" in entry for entry in entries):
        raise ProbeFailure()
    summary["search_metadata_success"] = True
    summary["result_count"] = len(entries)
    if not entries:
        return 0

    path = None
    for entry in entries:
        eid = entry.get("eid")
        ident = entry.get("dc:identifier")
        if isinstance(eid, str) and re.fullmatch(r"2-s2\.0-[0-9]+", eid):
            path = "/abstract/eid/" + eid
            break
        if isinstance(ident, str) and re.fullmatch(r"SCOPUS_ID:[0-9]+", ident):
            path = "/abstract/scopus_id/" + ident.split(":", 1)[1]
            break
    if path is None:
        raise ProbeFailure()
    summary["abstract_attempted"] = True
    body = _fetch(summary, "abstract", path, None, api_key, transport)
    core = body.get("abstracts-retrieval-response") if isinstance(body, dict) else None
    metadata = core.get("coredata") if isinstance(core, dict) else None
    if not isinstance(metadata, dict) or not metadata:
        raise ProbeFailure()
    summary["abstract_metadata_success"] = True
    description = metadata.get("dc:description")
    summary["abstract_present"] = isinstance(description, str) and bool(description.strip())
    return 0


def main():
    summary = {
        "search_http_success": False, "search_status": 0,
        "search_metadata_success": False, "result_count": 0,
        "abstract_attempted": False, "abstract_http_success": False,
        "abstract_status": 0, "abstract_metadata_success": False,
        "abstract_present": False, "abstract_access_denied": False,
    }
    try:
        code = _probe(summary)
    except (Exception, KeyboardInterrupt):
        # Even unexpected parser/network errors may contain licensed data or URLs.
        # Never print exception text, response content, headers, or identifiers.
        code = 1
    print(json.dumps(summary, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
