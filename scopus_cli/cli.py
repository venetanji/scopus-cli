"""Command-line interface for the Elsevier Scopus API."""

import json
import os
import sys

import click

from scopus_cli.client import ScopusClient, ScopusError

_API_KEY_ENV = "SCOPUS_API_KEY"


def _get_client(api_key: str | None) -> ScopusClient:
    key = api_key or os.environ.get(_API_KEY_ENV)
    if not key:
        raise click.UsageError(
            f"No API key provided.  Set the {_API_KEY_ENV} environment variable "
            "or pass --api-key."
        )
    return ScopusClient(key)


def _output(data: dict, raw: bool) -> None:
    """Print *data* as formatted JSON (default) or raw JSON when *raw* is True."""
    indent = None if raw else 2
    click.echo(json.dumps(data, indent=indent, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option()
def cli() -> None:
    """scopus-cli — command-line interface for the Elsevier Scopus API.

    Requires an Elsevier API key.  Set the SCOPUS_API_KEY environment variable
    or pass the --api-key option to any command.
    """


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@cli.command("search")
@click.argument("query")
@click.option("--count", default=25, show_default=True, help="Number of results.")
@click.option("--start", default=0, show_default=True, help="Result offset (pagination).")
@click.option(
    "--sort",
    default="relevancy",
    show_default=True,
    help="Sort field (relevancy, citedby-count, pubyear).",
)
@click.option("--api-key", envvar=_API_KEY_ENV, help="Elsevier API key.")
@click.option("--raw", is_flag=True, help="Output compact JSON.")
def search_cmd(query: str, count: int, start: int, sort: str, api_key: str | None, raw: bool) -> None:
    """Search the Scopus database.

    QUERY is a Scopus search string, e.g. 'TITLE-ABS-KEY(deep learning)'.
    """
    try:
        client = _get_client(api_key)
        data = client.search(query, count=count, start=start, sort=sort)
        _output(data, raw)
    except ScopusError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# abstract
# ---------------------------------------------------------------------------


@cli.command("abstract")
@click.option("--scopus-id", "scopus_id", default=None, help="Scopus article ID.")
@click.option("--doi", default=None, help="Article DOI.")
@click.option("--eid", default=None, help="Article EID.")
@click.option("--api-key", envvar=_API_KEY_ENV, help="Elsevier API key.")
@click.option("--raw", is_flag=True, help="Output compact JSON.")
def abstract_cmd(
    scopus_id: str | None,
    doi: str | None,
    eid: str | None,
    api_key: str | None,
    raw: bool,
) -> None:
    """Retrieve an article abstract.

    Provide exactly one of --scopus-id, --doi, or --eid.
    """
    identifiers = [x for x in (scopus_id, doi, eid) if x is not None]
    if len(identifiers) != 1:
        raise click.UsageError("Provide exactly one of --scopus-id, --doi, or --eid.")

    try:
        client = _get_client(api_key)
        if scopus_id:
            data = client.abstract_by_scopus_id(scopus_id)
        elif doi:
            data = client.abstract_by_doi(doi)
        elif eid:
            data = client.abstract_by_eid(eid)
        else:
            raise click.UsageError("Provide exactly one of --scopus-id, --doi, or --eid.")
        _output(data, raw)
    except ScopusError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# author
# ---------------------------------------------------------------------------


@cli.command("author")
@click.argument("author_id")
@click.option("--api-key", envvar=_API_KEY_ENV, help="Elsevier API key.")
@click.option("--raw", is_flag=True, help="Output compact JSON.")
def author_cmd(author_id: str, api_key: str | None, raw: bool) -> None:
    """Retrieve author information by AUTHOR_ID."""
    try:
        client = _get_client(api_key)
        data = client.author(author_id)
        _output(data, raw)
    except ScopusError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# author-search
# ---------------------------------------------------------------------------


@cli.command("author-search")
@click.argument("query")
@click.option("--count", default=25, show_default=True, help="Number of results.")
@click.option("--start", default=0, show_default=True, help="Result offset (pagination).")
@click.option("--api-key", envvar=_API_KEY_ENV, help="Elsevier API key.")
@click.option("--raw", is_flag=True, help="Output compact JSON.")
def author_search_cmd(query: str, count: int, start: int, api_key: str | None, raw: bool) -> None:
    """Search for authors.

    QUERY is a Scopus author search string, e.g. 'AUTHLASTNAME(Smith)'.
    """
    try:
        client = _get_client(api_key)
        data = client.author_search(query, count=count, start=start)
        _output(data, raw)
    except ScopusError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# citations
# ---------------------------------------------------------------------------


@cli.command("citations")
@click.argument("scopus_id")
@click.option("--api-key", envvar=_API_KEY_ENV, help="Elsevier API key.")
@click.option("--raw", is_flag=True, help="Output compact JSON.")
def citations_cmd(scopus_id: str, api_key: str | None, raw: bool) -> None:
    """Retrieve citation overview for an article by SCOPUS_ID."""
    try:
        client = _get_client(api_key)
        data = client.citations(scopus_id)
        _output(data, raw)
    except ScopusError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
