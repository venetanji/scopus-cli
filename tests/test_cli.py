"""Tests for the CLI commands."""

import json

import pytest
from click.testing import CliRunner

from scopus_cli.cli import cli

API_KEY = "test-key"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def env(monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setenv("SCOPUS_API_KEY", API_KEY)
    return {"SCOPUS_API_KEY": API_KEY}


class TestSearchCommand:
    def test_missing_api_key(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["search", "machine learning"])
        assert result.exit_code != 0
        assert "API key" in result.output or "Error" in result.output

    def test_search_success(self, runner: CliRunner, env: dict, mocker) -> None:
        mock_data = {"search-results": {"entry": [{"dc:title": "Paper A"}]}}
        mocker.patch("scopus_cli.cli.ScopusClient.search", return_value=mock_data)
        result = runner.invoke(cli, ["search", "deep learning"], env=env)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["search-results"]["entry"][0]["dc:title"] == "Paper A"

    def test_search_with_options(self, runner: CliRunner, env: dict, mocker) -> None:
        mock_client = mocker.patch("scopus_cli.cli.ScopusClient")
        mock_client.return_value.search.return_value = {}
        runner.invoke(
            cli,
            ["search", "neural networks", "--count", "10", "--start", "5", "--sort", "pubyear"],
            env=env,
        )
        mock_client.return_value.search.assert_called_once_with(
            "neural networks", count=10, start=5, sort="pubyear"
        )

    def test_search_raw_output(self, runner: CliRunner, env: dict, mocker) -> None:
        mock_data = {"key": "value"}
        mocker.patch("scopus_cli.cli.ScopusClient.search", return_value=mock_data)
        result = runner.invoke(cli, ["search", "test", "--raw"], env=env)
        assert result.exit_code == 0
        assert result.output.strip() == '{"key": "value"}'

    def test_search_api_error(self, runner: CliRunner, env: dict, mocker) -> None:
        from scopus_cli.client import ScopusError
        mocker.patch("scopus_cli.cli.ScopusClient.search", side_effect=ScopusError("401"))
        result = runner.invoke(cli, ["search", "test"], env=env)
        assert result.exit_code == 1


class TestAbstractCommand:
    def test_no_identifier(self, runner: CliRunner, env: dict) -> None:
        result = runner.invoke(cli, ["abstract"], env=env)
        assert result.exit_code != 0

    def test_multiple_identifiers(self, runner: CliRunner, env: dict) -> None:
        result = runner.invoke(
            cli, ["abstract", "--scopus-id", "123", "--doi", "10.1/x"], env=env
        )
        assert result.exit_code != 0
        assert "exactly one" in result.output.lower() or "Error" in result.output

    def test_abstract_by_scopus_id(self, runner: CliRunner, env: dict, mocker) -> None:
        mock_data = {"abstracts-retrieval-response": {}}
        mocker.patch(
            "scopus_cli.cli.ScopusClient.abstract_by_scopus_id", return_value=mock_data
        )
        result = runner.invoke(cli, ["abstract", "--scopus-id", "2-s2.0-85099143837"], env=env)
        assert result.exit_code == 0
        assert "abstracts-retrieval-response" in result.output

    def test_abstract_by_doi(self, runner: CliRunner, env: dict, mocker) -> None:
        mock_data = {"abstracts-retrieval-response": {}}
        mocker.patch("scopus_cli.cli.ScopusClient.abstract_by_doi", return_value=mock_data)
        result = runner.invoke(cli, ["abstract", "--doi", "10.1000/xyz123"], env=env)
        assert result.exit_code == 0

    def test_abstract_by_eid(self, runner: CliRunner, env: dict, mocker) -> None:
        mock_data = {"abstracts-retrieval-response": {}}
        mocker.patch("scopus_cli.cli.ScopusClient.abstract_by_eid", return_value=mock_data)
        result = runner.invoke(cli, ["abstract", "--eid", "2-s2.0-85099143837"], env=env)
        assert result.exit_code == 0


class TestAuthorCommand:
    def test_author_success(self, runner: CliRunner, env: dict, mocker) -> None:
        mock_data = {"author-retrieval-response": []}
        mocker.patch("scopus_cli.cli.ScopusClient.author", return_value=mock_data)
        result = runner.invoke(cli, ["author", "57204216842"], env=env)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "author-retrieval-response" in data

    def test_author_api_error(self, runner: CliRunner, env: dict, mocker) -> None:
        from scopus_cli.client import ScopusError
        mocker.patch("scopus_cli.cli.ScopusClient.author", side_effect=ScopusError("404"))
        result = runner.invoke(cli, ["author", "99999"], env=env)
        assert result.exit_code == 1


class TestAuthorSearchCommand:
    def test_author_search_success(self, runner: CliRunner, env: dict, mocker) -> None:
        mock_data = {"search-results": {"entry": []}}
        mocker.patch("scopus_cli.cli.ScopusClient.author_search", return_value=mock_data)
        result = runner.invoke(cli, ["author-search", "AUTHLASTNAME(Smith)"], env=env)
        assert result.exit_code == 0


class TestCitationsCommand:
    def test_citations_success(self, runner: CliRunner, env: dict, mocker) -> None:
        mock_data = {"abstract-citations-response": {}}
        mocker.patch("scopus_cli.cli.ScopusClient.citations", return_value=mock_data)
        result = runner.invoke(cli, ["citations", "2-s2.0-85099143837"], env=env)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "abstract-citations-response" in data


class TestApiKeyOption:
    def test_api_key_via_option(self, runner: CliRunner, mocker) -> None:
        mock_client_cls = mocker.patch("scopus_cli.cli.ScopusClient")
        mock_client_cls.return_value.search.return_value = {}
        result = runner.invoke(cli, ["search", "test", "--api-key", "mykey"])
        assert result.exit_code == 0
        mock_client_cls.assert_called_once_with("mykey")
