# MCP Servers

[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.36.3-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Keel](https://img.shields.io/badge/Keel-Kubernetes%20Operator-326CE5?logo=kubernetes&logoColor=white)](https://keel.sh/)
[![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io/)


A collection of Model Context Protocol (MCP) servers built with Python and FastMCP.

The repository currently contains three servers, all ready to run locally, build as Docker images, and deploy to Kubernetes.

| Server | Description |
|---|---|
| `example` | Minimal reference server showing how tools are structured. Use it as a template for new servers. |
| `runescape` | RuneScape Grand Exchange prices and player hiscore tracking, backed by PostgreSQL. |
| `remote_server_manager` | Opens persistent, interactive SSH shell sessions on remote hosts so an AI agent can run commands. |

All servers share the code in `shared/` (configuration, logging, database, error sanitization and Prometheus middleware), expose MCP over streamable HTTP at `/mcp` on `MCP_PORT`, and serve Prometheus metrics on `PROMETHEUS_PORT`.

## Remote Server Manager

Provides the following tools:

| Tool | Description |
|---|---|
| `create_ssh_session` | Connects to a host (password or key auth) and starts a shell with a PTY. Returns a `session_id`. |
| `send_to_ssh_session` | Sends a command or input to a session. A newline is appended automatically. |
| `read_from_ssh_session` | Reads buffered output from a session. Call repeatedly for long-running commands. |
| `list_ssh_sessions` | Lists open sessions with their host, user, activity timestamps and status. |
| `close_ssh_session` | Closes a session and frees its resources. |

> [!WARNING]
> This server gives an AI agent shell access to your machines. `send_to_ssh_session` blocks a list of destructive commands (recursive `rm`, `mkfs`, writing to disk devices, package removal, `systemctl stop`, `kill -9`, etc.), but that blocklist is a guardrail, not a security boundary. The MCP endpoint has no authentication and host keys are not verified.
>
> Read [SECURITY.md](SECURITY.md) for the full list of blocked commands, known limitations and hardening recommendations before deploying it.

Notes:

- **Sessions live in memory.** They are lost on restart and are not shared between pods, so keep `replicas: 1`.
- **Key-based auth** uses the default keys of the user running the server (`~/.ssh`). In Kubernetes, mount the key into the container if you are not using passwords.

## Quick Start

Install dependencies with uv:

```bash
uv sync
```


Each server includes an `.env.example` with the required configuration. Copy it to `.env`, configure it, and run the server from the repository root:

```bash
uv run python -m servers.example.main
```

### 1. Building

The included `build.sh` script handles Docker image builds and versioning.

Build a single server:

```bash
./build.sh runescape
```

### 2. Build all servers:

```bash
./build.sh --all
```


The script also supports version increments, cache control, and pushing images to the configured registry. See `./build.sh --help` for available options.

### 3. Kubernetes

Each server includes complete Kubernetes manifests under their respective `k8s/` directories:
```text
servers/
├── example/
│   └── k8s/
├── remote_server_manager/
│   └── k8s/
└── runescape/
    └── k8s/
```


The `deployment-example.yaml` and `secrets-example.yaml` files are templates. Copy them to `deployment.yaml` and `secrets.yaml` (both are git-ignored), fill in your registry and credentials, and remove the example files from the directory before applying.

After building and pushing an image, the manifests can be applied with `kubectl`:

```bash
kubectl apply -f servers/runescape/k8s/
```

## Contributing

PRs are very welcome! If you have improvements, new servers, tools, or ideas, feel free to open a pull request.