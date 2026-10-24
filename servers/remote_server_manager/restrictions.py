from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
import ipaddress
import re
import socket

from shared.errors import ConfigurationError


# Matches the start of a command: start of a line, after a separator (; & | ( ` $( quotes),
# optionally followed by wrappers like sudo, env, nohup or timeout, and an optional path (/usr/bin/).
# Used so that e.g. 'ssh' is only matched when it is run, not in 'systemctl status ssh' or '~/.ssh/config'.
_CMD = (
    r'(?:^|[;&|(`"\']|\$\()\s*'
    r'(?:(?:sudo|doas|env|nohup|exec|command|builtin|eval|time|nice|xargs|watch|timeout\s+\S+)\s+(?:-\S+\s+)*)*'
    r'(?:\S*/)?'
)
# Matches the end of a command name
_END = r'(?=\s|$|[;&|)`"\'])'


@dataclass(frozen=True)
class RestrictionGroup:
    description: str
    patterns: Tuple[str, ...]
    default: bool = True    # Enabled when not listed in ENABLED_RESTRICTIONS / DISABLED_RESTRICTIONS
    locked: bool = False    # Always enabled, cannot be disabled through configuration


RESTRICTION_GROUPS = {
    "destructive": RestrictionGroup(
        description="Recursive removal, disk writes and formatting, fork bombs, overwriting system files",
        locked=True,
        patterns=(
            # Recursive removal (rm -r, rm -rf, rm -fR, rm -i -r, rm --recursive)
            r'\brm\s+(?:-\S+\s+)*-[a-z]*r',
            r'\brm\s+.*--recursive\b',
            # System critical operations
            r'\bdd\b.*\bof=/dev/(?!null\b)',    # dd writing to a device
            r':\s*\(\s*\)\s*\{',                # Fork bomb :(){ :|:& };:
            r'>\s*/dev/(?:sd|hd|vd|xvd|nvme|mmcblk|dm-|mapper/|disk/)',     # Writing to block devices
            r'(?<!>)>(?!>)\s*/(?:bin|boot|etc|lib\w*|sbin|usr)/',          # Overwriting system files (>> append is allowed)
            # Disk formatting/partitioning (listing with -l is allowed)
            r'\bmkfs\b',
            r'\b[scg]?fdisk\b(?!\s+-l\b)',
            r'\bparted\b(?!\s+-l\b)',
            r'\bwipefs\b',
            # Recursive permission/ownership changes on / or system directories
            r'\bch(?:mod|own|grp)\b.*(?:\s-[a-z]*r|--recursive\b).*\s/(?:bin|boot|etc|home|lib\w*|opt|root|sbin|usr|var)?/?(?=\s|$)',
        ),
    ),
    "user_management": RestrictionGroup(
        description="Creating or deleting users and groups, editing account files",
        locked=True,
        patterns=(
            r'\b(?:useradd|adduser|userdel|deluser|newusers|groupadd|addgroup|groupdel|delgroup|vipw|vigr)\b',
            r'>\s*/etc/(?:passwd|shadow|group|gshadow)\b',             # Editing account files directly (> and >>)
            r'\btee\b.*\s/etc/(?:passwd|shadow|group|gshadow)\b',
            r'\bsed\b.*\s-i.*\s/etc/(?:passwd|shadow|group|gshadow)\b',
            r'\bpasswd\s+-[dD]',
            r'\busermod\s+-[dD]',
        ),
    ),
    "package_removal": RestrictionGroup(
        description="Uninstalling packages",
        patterns=(
            r'\bapt(?:-get)?\s+(?:remove|purge|autoremove)\b',
            r'\byum\s+remove\b',
            r'\bdnf\s+remove\b',
            r'\bpacman\s+-[Rr]',
            r'\bzypper\s+remove\b',
        ),
    ),
    "service_management": RestrictionGroup(
        description="Stopping services and force-killing processes",
        patterns=(
            r'\bsystemctl\s+stop\b',
            r'\bservice\s+[^\s]+\s+stop\b',
            r'\bkill\s+-9\b',
            r'\bkillall\b',
            r'\bpkill\b',
        ),
    ),
    "firewall": RestrictionGroup(
        description="Flushing or resetting firewall rules",
        patterns=(
            r'\biptables\s+-[Ff]',
            r'\bufw\s+reset\b',
        ),
    ),
    "remote_access": RestrictionGroup(
        description="Connecting from the remote host to other machines (ssh, scp, sftp, rsync, telnet, ...)",
        patterns=(
            _CMD + r'(?:ssh|scp|sftp|slogin|mosh|autossh|sshpass|ssh-copy-id|telnet|rlogin|rsh|rcp)' + _END,
            r'\brsync\b.*(?:\s(?:[\w.-]+@)?[\w.-]+::?|rsync://)',   # rsync to a remote host (host:path, host::module)
        ),
    ),
    "power": RestrictionGroup(
        description="Shutting down or rebooting the host",
        patterns=(
            _CMD + r'(?:shutdown|reboot|poweroff|halt)' + _END,
            r'\bsystemctl\s+(?:reboot|poweroff|halt|kexec|suspend|hibernate)\b',
            r'\b(?:init|telinit)\s+[06]\b',
        ),
    ),
    "remote_scripts": RestrictionGroup(
        description="Piping downloaded content straight into a shell (curl ... | sh)",
        patterns=(
            r'\b(?:curl|wget)\b[^|]*\|\s*(?:sudo\s+(?:-\S+\s+)*)?(?:\S*/)?(?:ba|da|k|z|fi)?sh\b',
        ),
    ),
    "privilege_escalation": RestrictionGroup(
        description="Running commands as another user (sudo, su, doas, pkexec)",
        default=False,
        patterns=(
            r'(?:^|[;&|(`"\']|\$\()\s*(?:\S*/)?(?:sudo|su|doas|pkexec)' + _END,
        ),
    ),
}

# Name used in error messages for patterns added through EXTRA_FORBIDDEN_PATTERNS
CUSTOM_GROUP = "custom"


def build_forbidden_patterns(
    enabled: List[str],
    disabled: List[str],
    extra_patterns: List[str],
) -> List[Tuple[str, re.Pattern]]:
    """
    Resolves which restriction groups are active and compiles their patterns.
    Returns a list of (group_name, compiled_pattern). Raises ConfigurationError on invalid configuration.
    """
    unknown = sorted(set(enabled + disabled) - RESTRICTION_GROUPS.keys())
    if unknown:
        raise ConfigurationError(
            f"Unknown restriction group(s): {', '.join(unknown)}. "
            f"Valid groups: {', '.join(RESTRICTION_GROUPS)}"
        )

    locked = sorted(name for name in disabled if RESTRICTION_GROUPS[name].locked)
    if locked:
        raise ConfigurationError(f"Restriction group(s) cannot be disabled: {', '.join(locked)}")

    conflicting = sorted(set(enabled) & set(disabled))
    if conflicting:
        raise ConfigurationError(f"Restriction group(s) both enabled and disabled: {', '.join(conflicting)}")

    patterns = []
    for name, group in RESTRICTION_GROUPS.items():
        if group.locked or name in enabled or (group.default and name not in disabled):
            patterns += [(name, re.compile(p, re.IGNORECASE | re.MULTILINE)) for p in group.patterns]

    for p in extra_patterns:
        try:
            patterns.append((CUSTOM_GROUP, re.compile(p, re.IGNORECASE | re.MULTILINE)))
        except re.error as e:
            raise ConfigurationError(f"Invalid pattern in EXTRA_FORBIDDEN_PATTERNS '{p}': {e}")

    return patterns


def active_groups(patterns: List[Tuple[str, re.Pattern]]) -> List[str]:
    """Returns the names of the groups that have at least one active pattern, in order."""
    return list(dict.fromkeys(name for name, _ in patterns))


def find_forbidden(patterns: List[Tuple[str, re.Pattern]], input_str: str) -> Optional[Tuple[str, str]]:
    """
    Check if the input contains any forbidden command patterns.
    Returns (group_name, pattern) of the first match, None otherwise.
    """
    for name, pattern in patterns:
        if pattern.search(input_str):
            return name, pattern.pattern
    return None


IPNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
IPAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


def parse_allowed_networks(entries: List[str]) -> List[IPNetwork]:
    """
    Parses ALLOWED_HOSTS entries (single IPs like 10.0.0.5 or CIDR ranges like 10.0.0.0/24).
    Raises ConfigurationError on invalid entries.
    """
    networks = []
    for entry in entries:
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            raise ConfigurationError(f"Invalid entry in ALLOWED_HOSTS '{entry}': expected an IP address or CIDR range")
    return networks


def _normalize(address: IPAddress) -> IPAddress:
    """Treats IPv4-mapped IPv6 addresses (::ffff:10.0.0.5) as their IPv4 address."""
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        return address.ipv4_mapped
    return address


def resolve_allowed_address(networks: List[IPNetwork], host: str, port: int) -> Optional[str]:
    """
    Resolves a hostname or IP and returns the first resolved address that falls within the allowed networks,
    or None if no resolved address is allowed. Connecting to the returned address (instead of the hostname)
    prevents DNS from resolving to a different address between the check and the connection.
    Raises ValueError if the host cannot be resolved.
    """
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError(f"Could not resolve host '{host}'")

    for info in infos:
        address = _normalize(ipaddress.ip_address(info[4][0].split("%")[0]))
        if any(address in network for network in networks):
            return str(address)
    return None
