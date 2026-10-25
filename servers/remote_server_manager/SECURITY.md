# Remote Server Manager Security

The `remote_server_manager` server lets an AI agent run a fixed set of operations on remote hosts over SSH. Read this document before deploying it.

## Security model

- **No shell access for the agent.** The agent cannot send commands or input to a host. Each tool runs predefined commands built by the server, without a PTY and in a fresh connection per call. Arguments are passed as quoted argument lists, so the remote shell only ever receives a single command with literal arguments.
- **Validated arguments.** Free-form arguments are limited to host names, which must exist in the inventory, and service names, which must match `^[A-Za-z0-9_][A-Za-z0-9_@.:-]*$` and therefore cannot inject shell syntax or options. Everything else is an enum or a bounded integer.
- **Host inventory.** The agent can only reach hosts listed in `HOSTS`, and only by name. Addresses, users and credentials are never passed through or returned by the tools.
- **Pinned host keys.** Connections are refused unless the host presents the `host_key` configured for it, so an attacker on the network cannot impersonate a host to capture its password.
- **Mutations are opt-in.** The only operation that changes anything is `restart_service`, and it only accepts services listed in that host's `restartable_services`.

## Known limitations

- **No authentication on the MCP endpoint.** Anyone who can reach the endpoint can use every tool on every host in the inventory.
- **Output is returned to the agent unfiltered.** Service logs and process lists can contain secrets. The agent can read the journal of any unit the SSH user has access to, and `get_service_status` and `list_services` work for every unit.
- **The SSH credentials could do more than the tools allow.** The server only runs its own commands, but if the server or its Secret were compromised, the key or passwords would give whatever access the SSH user has. Limit that user on the target hosts as described below.
- **Secrets are only base64-encoded.** Anyone who can read Secrets in the namespace can read the passwords and private key. Restrict that with RBAC, and consider enabling encryption at rest for Secrets.

## Hardening recommendations

- Connect with a **dedicated, unprivileged SSH user** on each target host. Do not use `root`.
- Prefer `SSH_PRIVATE_KEY` over passwords, so password login can stay disabled on the hosts. Use a **key used only by this server**, and restrict it in `authorized_keys`:

  ```
  from="10.0.0.0/24",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty ssh-ed25519 AAAA... remote-server-manager
  ```

- When `sudo = true`, allow only the restart commands the host is configured for, without a password:

  ```
  # /etc/sudoers.d/remote-server-manager
  mcp ALL=(root) NOPASSWD: /usr/bin/systemctl restart -- nginx.service, /usr/bin/systemctl restart -- myapp.service
  ```

- To let the user read system service logs, add it to the `systemd-journal` group. Otherwise it only sees its own journal.
- **Never expose the endpoint publicly.** Keep the Ingress internal, and restrict access with a Kubernetes `NetworkPolicy` or an authenticating reverse proxy.
- Restrict the pod's egress with a `NetworkPolicy` to the hosts in the inventory.
- Keep the `securityContext` from the example deployment: non-root user, read-only root filesystem, no privilege escalation, all capabilities dropped.

## Reporting a vulnerability

See the [repository security policy](../../SECURITY.md).
