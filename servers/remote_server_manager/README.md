# Remote Server Manager

An MCP server that lets an AI agent inspect and manage remote Linux hosts over SSH, through a fixed set of operations.

The agent never gets a shell. Each tool runs predefined commands that the server builds itself, and the agent can only choose a host from the inventory and fill in validated arguments such as a service name. It never sees addresses or credentials.

> [!WARNING]
> The MCP endpoint has no authentication. Read [SECURITY.md](SECURITY.md) before deploying it.

## Tools

| Tool | Description |
|---|---|
| `list_hosts` | Lists the hosts in the inventory and the services that may be restarted on each. |
| `get_system_info` | OS, kernel, uptime, load average, memory and disk usage of a host. |
| `list_processes` | Top processes by CPU or memory usage (up to 50). |
| `list_services` | systemd services that are running, failed, or all of them. |
| `get_service_status` | Active state, enabled state, main PID and restart count of a service. |
| `read_service_logs` | The most recent journal entries of a service (up to 500), optionally filtered by priority. |
| `restart_service` | Restarts a service. Only services listed in the host's `restartable_services` can be restarted. |

Target hosts need systemd, plus `ps`, `free` and `df` from procps and coreutils.

## Configuration

Everything is configured through environment variables: in the Secret ([`k8s/secrets-example.yaml`](k8s/secrets-example.yaml)) on Kubernetes, or in `.env` ([`.env.example`](.env.example)) for local runs.

Besides the settings shared by all servers (`MCP_NAME`, `MCP_PORT`, `PROMETHEUS_PORT`, `APP_VERSION`), this server reads:

| Variable | Required | Description |
|---|---|---|
| `HOSTS` | Yes | The hosts the agent can manage, in TOML. See below. |
| `SSH_PRIVATE_KEY` | For hosts without a password | Private key used to log in to every host that has no `password`. Must be unencrypted Ed25519, ECDSA or RSA. |

### Hosts

`HOSTS` has one `[name]` table per host. The agent refers to hosts by that name:

```yaml
stringData:
  HOSTS: |
    [web-01]
    address = "192.168.1.10"
    username = "mcp"
    host_key = "ssh-ed25519 AAAA..."
    sudo = true
    restartable_services = ["nginx", "myapp"]

    [db-01]
    address = "10.0.0.20"
    username = "mcp"
    password = "the-password"
    host_key = "ssh-ed25519 AAAA..."
```

| Setting | Required | Description |
|---|---|---|
| `address` | Yes | Hostname or IP address to connect to. |
| `username` | Yes | SSH user. Use a dedicated, least-privileged user, see [SECURITY.md](SECURITY.md). |
| `host_key` | Yes | The host's public SSH key. Connections are refused if the host presents a different key. |
| `password` | No | Log in with this password instead of `SSH_PRIVATE_KEY`. |
| `port` | No | SSH port, defaults to `22`. |
| `sudo` | No | Run `restart_service` as `sudo -n systemctl restart`. Defaults to `false`. |
| `restartable_services` | No | Services `restart_service` may restart. Leave it out to make the host read-only. |

To get a host's `host_key`, run this on the host and paste the output:

```bash
cat /etc/ssh/ssh_host_ed25519_key.pub
```

The configuration is validated at startup. Invalid TOML, an unknown setting, an invalid key or service name, or a host without a password while `SSH_PRIVATE_KEY` is unset stops the server, and the log says what is wrong.

## Running

From the repository root:

```bash
uv run python -m servers.remote_server_manager.main
```

See the [root README](../../README.md) for building the image and deploying to Kubernetes.

## Adding an operation

Tools live in [`tools/`](tools/). Each one opens a connection with `remote.connect(host)` and runs commands as argument lists with `conn.run()` or `conn.run_checked()`. The arguments are quoted with `shlex.join`, so the remote shell always receives a single command with literal arguments. Validate anything the agent supplies (see `inventory.normalize_service`), and never accept command text from the agent.
