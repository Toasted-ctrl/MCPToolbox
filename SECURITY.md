# Security Policy

## Reporting a Vulnerability

Please do **not** open a public issue for security problems. Report them privately through GitHub's [private vulnerability reporting](https://github.com/Toasted-ctrl/mcps/security/advisories/new) instead.

Include the affected server, the steps to reproduce, and the impact you expect. You will get a response as soon as possible.

## Supported Versions

Only the latest version of each server on the `main` branch receives security fixes.

## Remote Server Manager

The `remote_server_manager` server gives an AI agent interactive shell access to remote machines. Treat it as a high-risk component and read this section before deploying it.

### Command blocklist

`send_to_ssh_session` rejects input that matches a list of dangerous patterns before it is sent to the remote shell. The list lives in `_FORBIDDEN_COMMANDS` in [`servers/remote_server_manager/tools/ssh.py`](servers/remote_server_manager/tools/ssh.py).

| Blocked | Still allowed |
|---|---|
| Recursive removal: `rm -r`, `rm -rf`, `rm --recursive` | `rm file`, `rm -f file`, `rmdir` |
| `dd` writing to a device (`of=/dev/sda`) | `dd` to a file, e.g. `of=/tmp/backup.img` |
| Writing to block devices: `> /dev/sda` | `> /dev/null`, `2>/dev/null` |
| Overwriting files in `/etc`, `/boot`, `/bin`, `/sbin`, `/usr`, `/lib*` with `>` | Appending with `>>`, writing to `/tmp`, `/home`, `/var`, `/opt` |
| Fork bombs: `:(){ :\|:& };:` | |
| `mkfs`, `wipefs`, `fdisk`, `sfdisk`, `gdisk`, `cfdisk`, `parted` | `fdisk -l`, `parted -l`, `lsblk` |
| Package removal with `apt`, `yum`, `dnf`, `pacman` and `zypper` | Installing and updating packages |
| `systemctl stop`, `service <name> stop`, `kill -9`, `killall`, `pkill` | `systemctl status`, `systemctl restart` |
| Creating or deleting users and groups: `useradd`, `adduser`, `userdel`, `deluser`, `newusers`, `groupadd`, `addgroup`, `groupdel`, `delgroup`, `vipw`, `vigr` | Looking up users: `id`, `whoami`, `getent passwd`, `cat /etc/passwd` |
| Writing to `/etc/passwd`, `/etc/shadow`, `/etc/group` or `/etc/gshadow` with `>`, `>>`, `tee` or `sed -i` | |
| `passwd -d`, `usermod -d` | |
| Recursive `chmod` / `chown` / `chgrp` on `/` or top-level system directories | Recursive changes on subdirectories, e.g. `/var/www/app` |
| `iptables -F`, `ufw reset` | |

**The blocklist is a guardrail, not a security boundary.** It catches accidental or naive destructive commands, but pattern matching is easy to bypass with quoting, variables, `bash -c`, aliases, or scripts written to disk and executed. Do not rely on it to keep a determined or misbehaving agent in check.

### Known limitations

- **No authentication on the MCP endpoint.** Anyone who can reach the endpoint can open SSH sessions to any host the pod can reach, using credentials they supply or the keys available to the server.
- **Host keys are not verified.** Unknown host keys are accepted automatically (`paramiko.AutoAddPolicy`), which leaves connections open to man-in-the-middle attacks on untrusted networks.
- **Sessions never expire.** Idle sessions stay open until they are closed explicitly or the server restarts.
- **Command output is returned to the AI agent unfiltered**, including any secrets printed by the remote shell.

SSH passwords passed to `create_ssh_session` are masked (`***`) in the request logs.

### Hardening recommendations

- Connect with a **dedicated, least-privileged SSH user** on each target host. Do not use `root`.
- Restrict or disable `sudo` for that user, or limit it to specific commands in `sudoers`.
- Prefer **key-based authentication** with a key used only by this server, and restrict it on the target with `authorized_keys` options (`from=`, `no-port-forwarding`, `no-agent-forwarding`).
- **Never expose the endpoint publicly.** Keep the Ingress internal, and restrict access with Kubernetes `NetworkPolicy` or an authenticating reverse proxy.
- Restrict the pod's egress with a `NetworkPolicy` so it can only reach the hosts it is meant to manage.
- Keep the `securityContext` from the example deployment: non-root user, read-only root filesystem, no privilege escalation, all capabilities dropped.
