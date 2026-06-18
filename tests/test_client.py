"""Tests for the Scopus API client."""

import pytest
import responses as rsps_lib

from scopus_cli.client import ScopusClient, ScopusError

API_KEY = "test-api-key"
BASE_URL = "https://api.elsevier.com"


@pytest.fixture()
def client() -> ScopusClient:
    return ScopusClient(api_key=API_KEY)


class TestScopusClientHeaders:
    def test_api_key_header(self, client: ScopusClient) -> None:
        assert client._session.headers["X-ELS-APIKey"] == API_KEY

    def test_accept_header(self, client: ScopusClient) -> None:
        assert client._session.headers["Accept"] == "application/json"


class TestSearch:
    @rsps_lib.activate
    def test_search_success(self, client: ScopusClient) -> None:
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/search/scopus",
            json={"search-results": {"entry": [{"dc:title": "Paper A"}]}},
            status=200,
        )
        result = client.search("machine learning")
        assert result["search-results"]["entry"][0]["dc:title"] == "Paper A"

    @rsps_lib.activate
    def test_search_passes_params(self, client: ScopusClient) -> None:
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/search/scopus",
            json={},
            status=200,
        )
        client.search("deep learning", count=10, start=5, sort="citedby-count")
        request = rsps_lib.calls[0].request
        assert "query=deep+learning" in request.url or "query=deep%20learning" in request.url
        assert "count=10" in request.url
        assert "start=5" in request.url
        assert "sort=citedby-count" in request.url

    @rsps_lib.activate
    def test_search_api_error(self, client: ScopusClient) -> None:
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/search/scopus",
            json={"error": "Unauthorized"},
            status=401,
        )
        with pytest.raises(ScopusError, match="401"):
            client.search("test")


class TestAbstract:
    @rsps_lib.activate
    def test_abstract_by_scopus_id(self, client: ScopusClient) -> None:
        sid = "2-s2.0-85099143837"
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/abstract/scopus_id/{sid}",
            json={"abstracts-retrieval-response": {"coredata": {"dc:title": "Test"}}},
            status=200,
        )
        result = client.abstract_by_scopus_id(sid)
        assert result["abstracts-retrieval-response"]["coredata"]["dc:title"] == "Test"

    @rsps_lib.activate
    def test_abstract_by_doi(self, client: ScopusClient) -> None:
        doi = "10.1000/xyz123"
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/abstract/doi/{doi}",
            json={"abstracts-retrieval-response": {}},
            status=200,
        )
        result = client.abstract_by_doi(doi)
        assert "abstracts-retrieval-response" in result

    @rsps_lib.activate
    def test_abstract_by_eid(self, client: ScopusClient) -> None:
        eid = "2-s2.0-85099143837"
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/abstract/eid/{eid}",
            json={"abstracts-retrieval-response": {}},
            status=200,
        )
        result = client.abstract_by_eid(eid)
        assert "abstracts-retrieval-response" in result


class TestAuthor:
    @rsps_lib.activate
    def test_author_success(self, client: ScopusClient) -> None:
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/author/author_id/57204216842",
            json={"author-retrieval-response": [{"coredata": {"dc:identifier": "57204216842"}}]},
            status=200,
        )
        result = client.author("57204216842")
        assert "author-retrieval-response" in result

    @rsps_lib.activate
    def test_author_search_success(self, client: ScopusClient) -> None:
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/search/author",
            json={"search-results": {"entry": []}},
            status=200,
        )
        result = client.author_search("AUTHLASTNAME(Smith)")
        assert "search-results" in result


class TestCitations:
    @rsps_lib.activate
    def test_citations_success(self, client: ScopusClient) -> None:
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/abstract/citations",
            json={"abstract-citations-response": {}},
            status=200,
        )
        result = client.citations("2-s2.0-85099143837")
        assert "abstract-citations-response" in result


class TestErrorHandling:
    @rsps_lib.activate
    def test_connection_error(self, client: ScopusClient) -> None:
        import requests as req_lib
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/search/scopus",
            body=req_lib.exceptions.ConnectionError("connection refused"),
        )
        with pytest.raises(ScopusError, match="Connection error"):
            client.search("test")

    @rsps_lib.activate
    def test_invalid_json_response(self, client: ScopusClient) -> None:
        rsps_lib.add(
            rsps_lib.GET,
            f"{BASE_URL}/content/search/scopus",
            body=b"not-json",
            status=200,
            content_type="application/json",
        )
        with pytest.raises(ScopusError, match="JSON"):
            client.search("test")
