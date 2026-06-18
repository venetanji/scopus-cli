"""Client for the Elsevier Scopus API."""

import requests

BASE_URL = "https://api.elsevier.com"


class ScopusError(Exception):
    """Raised when the Scopus API returns an error response."""


class ScopusClient:
    """Thin wrapper around the Elsevier Scopus REST API.

    Parameters
    ----------
    api_key:
        Elsevier API key.  Obtain one at https://dev.elsevier.com/.
    timeout:
        HTTP request timeout in seconds (default: 30).
    """

    def __init__(self, api_key: str, timeout: int = 30) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-ELS-APIKey": api_key,
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        count: int = 25,
        start: int = 0,
        sort: str = "relevancy",
    ) -> dict:
        """Search the Scopus database.

        Parameters
        ----------
        query:
            Scopus search query (e.g. ``TITLE-ABS-KEY(machine learning)``).
        count:
            Number of results to return (max 200).
        start:
            Index of the first result (for pagination).
        sort:
            Sort field.  Common values: ``relevancy``, ``citedby-count``,
            ``pubyear``.

        Returns
        -------
        dict
            Parsed JSON response from the API.
        """
        url = f"{BASE_URL}/content/search/scopus"
        params = {
            "query": query,
            "count": count,
            "start": start,
            "sort": sort,
        }
        return self._get(url, params=params)

    # ------------------------------------------------------------------
    # Abstract / article retrieval
    # ------------------------------------------------------------------

    def abstract_by_scopus_id(self, scopus_id: str) -> dict:
        """Retrieve an article abstract by its Scopus ID.

        Parameters
        ----------
        scopus_id:
            Scopus identifier, e.g. ``2-s2.0-85099143837``.
        """
        url = f"{BASE_URL}/content/abstract/scopus_id/{scopus_id}"
        return self._get(url)

    def abstract_by_doi(self, doi: str) -> dict:
        """Retrieve an article abstract by DOI.

        Parameters
        ----------
        doi:
            Digital Object Identifier, e.g. ``10.1000/xyz123``.
        """
        url = f"{BASE_URL}/content/abstract/doi/{doi}"
        return self._get(url)

    def abstract_by_eid(self, eid: str) -> dict:
        """Retrieve an article abstract by EID.

        Parameters
        ----------
        eid:
            Electronic Identifier, e.g. ``2-s2.0-85099143837``.
        """
        url = f"{BASE_URL}/content/abstract/eid/{eid}"
        return self._get(url)

    # ------------------------------------------------------------------
    # Author retrieval
    # ------------------------------------------------------------------

    def author(self, author_id: str) -> dict:
        """Retrieve author information by author ID.

        Parameters
        ----------
        author_id:
            Scopus author identifier, e.g. ``57204216842``.
        """
        url = f"{BASE_URL}/content/author/author_id/{author_id}"
        return self._get(url)

    def author_search(self, query: str, count: int = 25, start: int = 0) -> dict:
        """Search for authors.

        Parameters
        ----------
        query:
            Author search query, e.g. ``AUTHLASTNAME(Smith)``.
        count:
            Number of results to return.
        start:
            Index of the first result (for pagination).
        """
        url = f"{BASE_URL}/content/search/author"
        params = {"query": query, "count": count, "start": start}
        return self._get(url, params=params)

    # ------------------------------------------------------------------
    # Citations
    # ------------------------------------------------------------------

    def citations(self, scopus_id: str) -> dict:
        """Retrieve citation overview for an article.

        Parameters
        ----------
        scopus_id:
            Scopus identifier, e.g. ``2-s2.0-85099143837``.
        """
        url = f"{BASE_URL}/content/abstract/citations"
        params = {"scopus_id": scopus_id}
        return self._get(url, params=params)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict | None = None) -> dict:
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.ConnectionError as exc:
            raise ScopusError(f"Connection error: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            raise ScopusError(f"Request timed out after {self.timeout}s") from exc

        if not response.ok:
            raise ScopusError(
                f"API request failed with status {response.status_code}: "
                f"{response.text[:200]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ScopusError(f"Failed to parse API response as JSON: {exc}") from exc
