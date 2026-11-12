# Contributing

PRs are very welcome! This guide covers how to set up the repository, add tools and servers, and run the checks a pull request has to pass.

For larger changes, such as a new server, consider opening an issue first so the approach can be discussed.

> [!IMPORTANT]
> Please do **not** report security problems in issues or pull requests. Follow [SECURITY.md](SECURITY.md) instead.

## Development Setup

Install dependencies, including the development tools, with uv:

```bash
uv sync
```

Each server includes an `.env.example` with the required configuration. Copy it to `.env`, configure it, and run the server from the repository root:

```bash
cp servers/example/.env.example servers/example/.env
uv run python -m servers.example.main
```

The server exposes MCP over streamable HTTP at `http://localhost:<MCP_PORT>/mcp` and Prometheus metrics on `PROMETHEUS_PORT`.

## Project Structure

```text
├── shared/                  # Code shared by all servers
│   ├── config.py            # BaseConfig: loads and validates environment variables
│   ├── db.py                # Database sessions
│   ├── errors.py            # Exceptions such as NotFoundError
│   ├── logger.py
│   └── middleware/          # Error sanitization and Prometheus metrics
├── servers/
│   └── <server>/
│       ├── main.py          # Entry point, imports the tools
│       ├── server.py        # FastMCP instance and middleware
│       ├── config.py        # Server-specific configuration
│       ├── tools/           # One module per tool, or per group of tools
│       ├── k8s/             # Kubernetes manifests
│       ├── Dockerfile
│       └── .env.example
└── tests/                   # Mirrors the layout of the code it tests
```

## Adding a Tool

1. Create a module in the server's `tools/` directory and register the tool on the server's `mcp` instance:

    ```python
    from typing import Annotated

    from pydantic import Field

    from ..server import mcp


    @mcp.tool(
        name="sum_integers",
        version="1.0.0",
        description="Sums a list of integers",
        meta={"author": "<your GitHub username>"},
    )
    def sum_integers(
        integers: Annotated[list[int], Field(description="List of integers")],
    ) -> dict:
        if len(integers) < 2:
            raise ValueError("At least two integers must be provided.")
        return {"result": sum(integers)}
    ```

2. Import the module in the server's `main.py`. Tools are registered when their module is imported, so a tool that isn't imported there won't be available:

    ```python
    from .tools import files, iterate_list_dicts, sum_integers
    ```

    These imports look unused, so ruff's unused-import rule (F401) is disabled for `servers/*/main.py`. Don't remove them.

A few things to keep in mind:

- **Write descriptions for the agent.** The tool and parameter descriptions are all the agent knows about a tool. Say what it returns, and when it should and should not be used.
- **Raise the right exceptions.** Errors are sanitized before they reach the client. `ValueError`, `TypeError`, `KeyError`, `NotImplementedError` and `NotFoundError` (from `shared.errors`) pass through with their message. Any other exception is replaced with a generic error, so database details, file paths and hostnames don't leak. Use a safe exception when the agent needs to know what went wrong, and keep sensitive details out of its message. A server can allow additional exceptions, as `remote_server_manager` does with `RemoteError`.
- **Bump the tool's `version`** when you change its behaviour.

## Adding a Server

Use [`servers/example`](servers/example) as a template:

1. Copy `servers/example` to `servers/<your_server>`.
2. Update the `COPY` and `CMD` lines in the `Dockerfile`, and set `MCP_NAME` in `.env.example`.
3. If the server needs more environment variables, add them to `ADDITIONAL_VARS` in its `config.py`, and to `.env.example` and `k8s/secrets-example.yaml`.
4. Update the manifests in `k8s/` for the new server.
5. Add the server to the table in the [README](README.md). If it has tools or configuration worth documenting, give it its own `README.md`. If it gives an agent access to real systems, add a `SECURITY.md` covering its security model and limitations, like [`remote_server_manager`](servers/remote_server_manager/SECURITY.md) does.

## Checks

Pull requests have to pass the same checks that run in CI:

```bash
uv run ruff format --check servers shared tests
uv run ruff check servers shared tests
uv run mypy servers shared tests
uv run pytest
```

Run `uv run ruff format servers shared tests` to fix formatting.

The Docker images run Python 3.12, so code must work on 3.12. Ruff and mypy target 3.12 and flag newer syntax, and CI runs the tests on both Python 3.12 and 3.14.

Changes to `shared/` should come with tests in `tests/shared/`.

## Dependencies

Add or remove dependencies with uv, which also updates `uv.lock`:

```bash
uv add <package>
uv add --dev <package>
```

Commit `uv.lock` together with `pyproject.toml`. CI installs with `uv sync --locked` and fails if the lockfile is out of date.

## Pull Requests

- Keep each pull request focused on one change, and describe what it changes and why.
- Update the README and any server documentation affected by the change.
- Never commit `.env`, `secrets.yaml` or `deployment.yaml` files, or any credentials. They are git-ignored, keep them that way.
