# scopus-cli

A command-line interface for the [Elsevier Scopus API](https://dev.elsevier.com/api_docs.html).

## Installation

```bash
pip install -e .
```

## Authentication

Obtain an API key from [Elsevier Developer Portal](https://dev.elsevier.com/) and export it:

```bash
export SCOPUS_API_KEY=your_api_key_here
```

Alternatively, pass it directly to any command via `--api-key`.

## Commands

### Search articles

```bash
scopus search "TITLE-ABS-KEY(deep learning)"
scopus search "TITLE-ABS-KEY(machine learning)" --count 10 --sort citedby-count
scopus search "AU-ID(57204216842)" --start 0 --count 25
```

### Retrieve an abstract

```bash
# by Scopus ID
scopus abstract --scopus-id 2-s2.0-85099143837

# by DOI
scopus abstract --doi 10.1016/j.neunet.2020.01.013

# by EID
scopus abstract --eid 2-s2.0-85099143837
```

### Retrieve author information

```bash
scopus author 57204216842
```

### Search for authors

```bash
scopus author-search "AUTHLASTNAME(Smith) AND AUTHFIRST(John)"
```

### Citation overview

```bash
scopus citations 2-s2.0-85099143837
```

## Options

All commands support:

| Option | Description |
|--------|-------------|
| `--api-key TEXT` | Elsevier API key (overrides `SCOPUS_API_KEY`) |
| `--raw` | Output compact (unindented) JSON |
| `--help` | Show command help |

## Development

```bash
pip install -e ".[dev]"
pytest
```
