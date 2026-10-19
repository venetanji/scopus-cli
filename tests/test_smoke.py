import contextlib
import io
import json
import os
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest import mock

from scopus_cli import cli, smoke


SECRET = "fake-api-key-never-log"
PRIVATE = "licensed-content-never-log"


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self, body):
        super().__init__(json.dumps(body).encode())


def search(entries=None, total="5"):
    if entries is None:
        entries = [{"eid": "2-s2.0-{}".format(i), "dc:title": PRIVATE}
                   for i in range(1, 6)]
    return {"search-results": {"entry": entries, "opensearch:totalResults": total}}


def abstract(description=PRIVATE):
    return {"abstracts-retrieval-response": {"coredata": {
        "dc:title": PRIVATE, "dc:description": description}}}


class SmokeTests(unittest.TestCase):
    def probe(self, responses, key=SECRET):
        stdout, stderr = io.StringIO(), io.StringIO()
        env = {"SCOPUS_API_KEY": key} if key else {}
        # All network access is mocked at the real transport boundary.
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch("urllib.request.OpenerDirector.open", side_effect=responses) as opened, \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = smoke.main()
        output = stdout.getvalue()
        self.assertEqual(stderr.getvalue(), "")
        self.assertNotIn(SECRET, output)
        self.assertNotIn(PRIVATE, output)
        self.assertNotIn(smoke.QUERY, output)
        summary = json.loads(output)
        self.assertTrue(all(type(v) in (bool, int) for v in summary.values()))
        return code, summary, opened

    def test_uses_real_cli_request_logic_with_two_bounded_requests(self):
        with mock.patch.object(cli, "_get", wraps=cli._get) as get:
            code, summary, opened = self.probe([Response(search()), Response(abstract())])
        self.assertEqual(code, 0)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(opened.call_count, 2)
        self.assertEqual(summary["result_count"], 5)
        self.assertTrue(summary["search_metadata_success"])
        self.assertTrue(summary["abstract_metadata_success"])
        self.assertTrue(summary["abstract_present"])
        self.assertEqual(summary["search_status"], 200)
        self.assertEqual(summary["abstract_status"], 200)
        first, second = [call.args[0] for call in opened.call_args_list]
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(first.full_url).query)
        self.assertEqual(query["count"], ["5"])
        self.assertEqual(query["start"], ["0"])
        self.assertEqual(query["view"], ["STANDARD"])
        self.assertEqual(query["query"], [smoke.QUERY])
        self.assertEqual(second.full_url, cli.BASE + "/abstract/eid/2-s2.0-1")
        for call in opened.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 10)
            self.assertEqual(call.args[0].get_header("X-els-apikey"), SECRET)
            self.assertNotIn(SECRET, call.args[0].full_url)

    def test_missing_key_makes_no_requests(self):
        code, summary, opened = self.probe([], key=None)
        self.assertEqual(code, 1)
        self.assertFalse(summary["search_http_success"])
        self.assertEqual(opened.call_count, 0)

    def test_zero_results_skip_abstract(self):
        for entries in ([], [{"error": PRIVATE}]):
            with self.subTest(entries=entries):
                code, summary, opened = self.probe([Response(search(entries, "0"))])
                self.assertEqual(code, 0)
                self.assertEqual(summary["result_count"], 0)
                self.assertTrue(summary["search_metadata_success"])
                self.assertFalse(summary["abstract_attempted"])
                self.assertEqual(opened.call_count, 1)

    def test_no_usable_identifier_does_not_construct_an_abstract_url(self):
        for eid in (None, "2-s2.0-1/../../leak?key=" + SECRET, 123):
            with self.subTest(eid=eid):
                code, summary, opened = self.probe([Response(search([{"eid": eid}], "1"))])
                self.assertEqual(code, 1)
                self.assertFalse(summary["abstract_attempted"])
                self.assertEqual(opened.call_count, 1)

    def test_numeric_scopus_identifier_fallback_comes_from_search(self):
        code, summary, opened = self.probe([
            Response(search([{"dc:identifier": "SCOPUS_ID:12345"}], "1")),
            Response(abstract())])
        self.assertEqual(code, 0)
        self.assertEqual(opened.call_args_list[1].args[0].full_url,
                         cli.BASE + "/abstract/scopus_id/12345")

    def test_missing_abstract_text_is_separate_from_metadata_success(self):
        code, summary, _ = self.probe([Response(search()), Response(abstract(None))])
        self.assertEqual(code, 0)
        self.assertTrue(summary["abstract_metadata_success"])
        self.assertFalse(summary["abstract_present"])
        self.assertFalse(summary["abstract_access_denied"])

    def test_denied_abstract_access_does_not_hide_search_success(self):
        for status in (401, 403):
            with self.subTest(status=status):
                error = urllib.error.HTTPError("https://invalid/" + SECRET, status,
                                               PRIVATE, {}, io.BytesIO(PRIVATE.encode()))
                with mock.patch.object(error, "read", side_effect=AssertionError("must not read")):
                    code, summary, _ = self.probe([Response(search()), error])
                self.assertEqual(code, 1)
                self.assertTrue(summary["search_metadata_success"])
                self.assertFalse(summary["abstract_metadata_success"])
                self.assertTrue(summary["abstract_access_denied"])
                self.assertEqual(summary["abstract_status"], status)

    def test_http_network_and_unexpected_errors_never_print_details_or_retry(self):
        errors = [urllib.error.HTTPError("https://invalid/" + SECRET, 429, PRIVATE, {},
                                         io.BytesIO(PRIVATE.encode())),
                  urllib.error.URLError(SECRET + PRIVATE),
                  TimeoutError(SECRET + PRIVATE), RuntimeError(SECRET + PRIVATE)]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                code, summary, opened = self.probe([error])
                self.assertEqual(code, 1)
                self.assertFalse(summary["search_metadata_success"])
                self.assertEqual(opened.call_count, 1)

    def test_malformed_or_excessive_search_results_fail_closed(self):
        bodies = [[], {}, {"search-results": []},
                  search("not a list"), search([None]), search([{}] * 6),
                  search([{"error": PRIVATE}], "1")]
        for body in bodies:
            with self.subTest(body=body):
                code, summary, opened = self.probe([Response(body)])
                self.assertEqual(code, 1)
                self.assertFalse(summary["search_metadata_success"])
                self.assertEqual(opened.call_count, 1)

    def test_invalid_json_and_oversized_responses_fail_without_content(self):
        for content in (PRIVATE.encode(), b" " * (smoke.MAX_RESPONSE_BYTES + 1)):
            response = Response({})
            response.seek(0)
            response.write(content)
            response.seek(0)
            with self.subTest(size=len(content)), mock.patch.object(response, "read", wraps=response.read) as read:
                code, summary, _ = self.probe([response])
                self.assertEqual(code, 1)
                self.assertFalse(summary["search_metadata_success"])
                self.assertEqual(read.call_args.args, (smoke.MAX_RESPONSE_BYTES + 1,))

    def test_bad_abstract_schema_fails_without_printing_content(self):
        for body in ({}, {"abstracts-retrieval-response": []},
                     {"abstracts-retrieval-response": {"coredata": {}}}):
            with self.subTest(body=body):
                code, summary, _ = self.probe([Response(search()), Response(body)])
                self.assertEqual(code, 1)
                self.assertFalse(summary["abstract_metadata_success"])

    def test_transport_enforces_request_budget(self):
        transport = smoke.BoundedTransport()
        request = urllib.request.Request(cli.BASE)
        with mock.patch("urllib.request.OpenerDirector.open", side_effect=[Response({}), Response({})]) as opened:
            for _ in range(2):
                with transport(request, timeout=30) as response:
                    response.read()
            with self.assertRaises(smoke.ProbeFailure):
                transport(request, timeout=30)
        self.assertEqual(opened.call_count, 2)

    def test_expired_time_budget_prevents_requests(self):
        with mock.patch.object(smoke.time, "monotonic", return_value=0):
            transport = smoke.BoundedTransport()
        with mock.patch.object(smoke.time, "monotonic", return_value=smoke.PROBE_TIMEOUT), \
                mock.patch("urllib.request.OpenerDirector.open") as opened:
            with self.assertRaises(smoke.ProbeFailure):
                transport(urllib.request.Request(cli.BASE), timeout=30)
        opened.assert_not_called()

    def test_expired_time_budget_prevents_body_read(self):
        response = Response({})
        bounded = smoke.BoundedResponse(response, deadline=25)
        with mock.patch.object(smoke.time, "monotonic", return_value=25), \
                mock.patch.object(response, "read") as read:
            with bounded, self.assertRaises(smoke.ProbeFailure):
                bounded.read()
        read.assert_not_called()
        self.assertTrue(response.closed)

    def test_slow_body_is_rejected_after_read(self):
        response = Response({})
        with mock.patch.object(smoke.time, "monotonic", side_effect=[24, 26]):
            with smoke.BoundedResponse(response, deadline=25) as bounded:
                with self.assertRaises(smoke.ProbeFailure):
                    bounded.read()
        self.assertTrue(response.closed)

    def test_redirect_handler_never_follows_locations(self):
        self.assertIsNone(smoke.NoRedirect().redirect_request(None, None, 302, PRIVATE, {},
                                                             "https://invalid/" + SECRET))

    def test_cli_default_transport_still_works(self):
        with mock.patch("urllib.request.urlopen", return_value=Response({"ok": True})) as opened:
            body, _ = cli._get("/search/scopus", {"count": 5}, SECRET)
        self.assertEqual(body, {"ok": True})
        self.assertEqual(opened.call_args.kwargs["timeout"], 30)


if __name__ == "__main__":
    unittest.main()
