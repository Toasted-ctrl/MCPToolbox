# Remote Server Manager Security

The `remote_server_manager` server gives an AI agent interactive shell access to remote machines. Treat it as a high-risk component and read this document before deploying it.

## Command blocklist

`send_to_ssh_session` rejects input that matches a list of dangerous patterns before it is sent to the remote shell. The patterns are organised into restriction groups in [`restrictions.py`](restrictions.py).

| Group | Default | Blocked | Still allowed |
|---|---|---|---|
| `destructive` | Always on | Recursive removal (`rm -r`, `rm -rf`, `rm --recursive`); `dd` writing to a device (`of=/dev/sda`); writing to block devices (`> /dev/sda`); overwriting files in `/etc`, `/boot`, `/bin`, `/sbin`, `/usr`, `/lib*` with `>`; fork bombs; `mkfs`, `wipefs`, `fdisk`, `sfdisk`, `gdisk`, `cfdisk`, `parted`; recursive `chmod` / `chown` / `chgrp` on `/` or top-level system directories | `rm file`, `rm -f file`, `rmdir`; `dd` to a file; `> /dev/null`; appending with `>>`; writing to `/tmp`, `/home`, `/var`, `/opt`; `fdisk -l`, `parted -l`, `lsblk`; recursive changes on subdirectories, e.g. `/var/www/app` |
| `user_management` | Always on | `useradd`, `adduser`, `userdel`, `deluser`, `newusers`, `groupadd`, `addgroup`, `groupdel`, `delgroup`, `vipw`, `vigr`; writing to `/etc/passwd`, `/etc/shadow`, `/etc/group` or `/etc/gshadow` with `>`, `>>`, `tee` or `sed -i`; `passwd -d`, `usermod -d` | `id`, `whoami`, `getent passwd`, `cat /etc/passwd` |
| `package_removal` | On | Package removal with `apt`/`apt-get` (`remove`, `purge`, `autoremove`), `yum`, `dnf`, `pacman` and `zypper` | Installing and updating packages |
| `service_management` | On | `systemctl stop`, `service <name> stop`, `kill -9`, `killall`, `pkill` | `systemctl status`, `systemctl restart` |
| `firewall` | On | `iptables -F`, `ufw reset` | Listing rules |
| `remote_access` | On | Connecting from the remote host to other machines: `ssh`, `scp`, `sftp`, `slogin`, `mosh`, `autossh`, `sshpass`, `ssh-copy-id`, `telnet`, `rlogin`, `rsh`, `rcp`, and `rsync` to a remote host (`host:path`, `rsync://`) | `ssh-keygen`, `systemctl status ssh`, reading `~/.ssh/config` or `/etc/ssh/`, local `rsync` |
| `power` | On | `shutdown`, `reboot`, `poweroff`, `halt`, `systemctl reboot/poweroff/halt/kexec/suspend/hibernate`, `init 0`, `init 6` | `last reboot`, searching logs for "shutdown" |
| `remote_scripts` | On | Piping downloaded content into a shell: `curl ... \| sh`, `wget -O- ... \| sudo bash` | Downloading to a file, `curl ... \| jq` |
| `privilege_escalation` | Off | `sudo`, `su`, `doas`, `pkexec` | |

### Configuring restrictions

The groups are configured with environment variables (in `.env` or the ConfigMap):

| Variable | Description |
|---|---|
| `ENABLED_RESTRICTIONS` | Comma-separated groups to turn on that are off by default, e.g. `privilege_escalation`. |
| `DISABLED_RESTRICTIONS` | Comma-separated groups to turn off that are on by default, e.g. `power,remote_access`. `destructive` and `user_management` cannot be disabled. |
| `EXTRA_FORBIDDEN_PATTERNS` | Additional case-insensitive regex patterns to block, one per line, e.g. `\bnc\b`. |

An unknown group name, an attempt to disable a locked group, or an invalid regex stops the server at startup. The active groups are logged when the server starts.

**The blocklist is a guardrail, not a security boundary.** It catches accidental or naive destructive commands, but pattern matching is easy to bypass with quoting, variables, `bash -c`, aliases, or scripts written to disk and executed. Do not rely on it to keep a determined or misbehaving agent in check.

## Host allowlist

`ALLOWED_HOSTS` limits which hosts `create_ssh_session` can connect to. It is a comma-separated list of IP addresses and CIDR ranges, set in the Secret (or `.env`):

```
ALLOWED_HOSTS="192.168.1.10,10.0.0.0/24,fd00::/64"
```

- Hostnames are resolved first, and the session is only created if a resolved IP is in the list. The server then connects to that IP directly, so DNS cannot point the hostname somewhere else between the check and the connection.
- Hosts that are not allowed are rejected before any connection is attempted.
- An invalid entry stops the server at startup.
- When `ALLOWED_HOSTS` is empty or unset, **all hosts are allowed** and a warning is logged at startup.

## Known limitations

- **No authentication on the MCP endpoint.** Anyone who can reach the endpoint can open SSH sessions to any host the pod can reach (or any host in `ALLOWED_HOSTS`, if set), using credentials they supply or the keys available to the server.
- **Host keys are not verified.** Unknown host keys are accepted automatically (`paramiko.AutoAddPolicy`), which leaves connections open to man-in-the-middle attacks on untrusted networks.
- **Sessions never expire.** Idle sessions stay open until they are closed explicitly or the server restarts.
- **Command output is returned to the AI agent unfiltered**, including any secrets printed by the remote shell.

SSH passwords passed to `create_ssh_session` are masked (`***`) in the request logs.

## Hardening recommendations

- Connect with a **dedicated, least-privileged SSH user** on each target host. Do not use `root`.
- Restrict or disable `sudo` for that user, or limit it to specific commands in `sudoers`.
- Prefer **key-based authentication** with a key used only by this server, and restrict it on the target with `authorized_keys` options (`from=`, `no-port-forwarding`, `no-agent-forwarding`).
- **Never expose the endpoint publicly.** Keep the Ingress internal, and restrict access with Kubernetes `NetworkPolicy` or an authenticating reverse proxy.
- Set `ALLOWED_HOSTS` to the hosts the server is meant to manage, and back it up by restricting the pod's egress with a `NetworkPolicy`.
- The `remote_access` group only stops the agent from *typing* `ssh` and similar commands. To actually prevent lateral movement, restrict outbound connections on the target hosts themselves (e.g. firewall egress rules for the SSH user), and do not leave private keys for other machines in that user's `~/.ssh`.
- Keep the `securityContext` from the example deployment: non-root user, read-only root filesystem, no privilege escalation, all capabilities dropped.

## Reporting a vulnerability

See the [repository security policy](../../SECURITY.md).
