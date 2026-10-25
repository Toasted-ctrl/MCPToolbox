from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import base64
import binascii
import io
import re
import tomllib

import paramiko

from shared.errors import ConfigurationError, NotFoundError

from .config import config


# Host names as used by the agent, and systemd unit names. Neither may start with '-' so they are never parsed as options.
_HOST_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
_SERVICE_NAME = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_@.:-]{0,254}$')

_HOST_KEYS = {"address", "port", "username", "password", "host_key", "sudo", "restartable_services"}


@dataclass(frozen=True)
class Host:
    name: str
    address: str
    port: int
    username: str
    password: Optional[str]                 # When not set, SSH_PRIVATE_KEY is used
    host_key: paramiko.PKey                 # The server's public key, connections with any other key are refused
    sudo: bool                              # Prefix mutating commands with 'sudo -n'
    restartable_services: Tuple[str, ...]   # Units restart_service may restart, normalized to 'name.service'


def normalize_service(service: str) -> str:
    """Validates a systemd unit name and appends '.service' when no unit type is given."""
    if not _SERVICE_NAME.match(service):
        raise ValueError(f"Invalid service name '{service}'")
    return service if "." in service else f"{service}.service"


def _parse_host_key(value: str) -> paramiko.PKey:
    """Parses a public key line as found in known_hosts or *.pub files: '[host] <type> <base64> [comment]'."""
    fields = value.split()
    for i, field in enumerate(fields[:-1]):
        if field.startswith(("ssh-", "ecdsa-")):
            try:
                return paramiko.PKey.from_type_string(field, base64.b64decode(fields[i + 1]))
            except (paramiko.SSHException, ValueError, binascii.Error):
                continue
    raise ValueError("expected a public key like 'ssh-ed25519 AAAA...'")


def _parse_private_key(value: str) -> paramiko.PKey:
    for key_class in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
        try:
            return key_class.from_private_key(io.StringIO(value))
        except (paramiko.SSHException, ValueError):
            continue
    raise ConfigurationError("SSH_PRIVATE_KEY is not a valid, unencrypted Ed25519, ECDSA or RSA private key")


def _parse_host(name: str, entry: dict) -> Host:
    where = f"host '{name}' in HOSTS"

    if not _HOST_NAME.match(name):
        raise ConfigurationError(f"Invalid host name '{name}' in HOSTS: use letters, digits, '.', '_' and '-'")
    if not isinstance(entry, dict):
        raise ConfigurationError(f"Invalid {where}: expected a table like [{name}]")

    unknown = sorted(entry.keys() - _HOST_KEYS)
    if unknown:
        raise ConfigurationError(f"Unknown setting(s) for {where}: {', '.join(unknown)}")

    for key in ("address", "username", "host_key"):
        if not isinstance(entry.get(key), str) or not entry[key]:
            raise ConfigurationError(f"Missing or invalid '{key}' for {where}")

    port = entry.get("port", 22)
    if not isinstance(port, int) or not 0 < port < 65536:
        raise ConfigurationError(f"Invalid 'port' for {where}")

    password = entry.get("password")
    if password is not None and (not isinstance(password, str) or not password):
        raise ConfigurationError(f"Invalid 'password' for {where}")
    if password is None and not config.SSH_PRIVATE_KEY:
        raise ConfigurationError(f"No 'password' for {where} and SSH_PRIVATE_KEY is not set")

    try:
        host_key = _parse_host_key(entry["host_key"])
    except ValueError as e:
        raise ConfigurationError(f"Invalid 'host_key' for {where}: {e}")

    sudo = entry.get("sudo", False)
    if not isinstance(sudo, bool):
        raise ConfigurationError(f"Invalid 'sudo' for {where}: expected true or false")

    services = entry.get("restartable_services", [])
    if not isinstance(services, list) or not all(isinstance(s, str) for s in services):
        raise ConfigurationError(f"Invalid 'restartable_services' for {where}: expected a list of service names")
    try:
        restartable = tuple(normalize_service(s) for s in services)
    except ValueError as e:
        raise ConfigurationError(f"Invalid 'restartable_services' for {where}: {e}")

    return Host(
        name=name,
        address=entry["address"],
        port=port,
        username=entry["username"],
        password=password,
        host_key=host_key,
        sudo=sudo,
        restartable_services=restartable,
    )


def load_hosts(value: str) -> Dict[str, Host]:
    """Parses and validates the HOSTS inventory. Raises ConfigurationError on invalid configuration."""
    try:
        data = tomllib.loads(value)
    except tomllib.TOMLDecodeError as e:
        raise ConfigurationError(f"HOSTS is not valid TOML: {e}")

    hosts = {name: _parse_host(name, entry) for name, entry in data.items()}
    if not hosts:
        raise ConfigurationError("No hosts defined in HOSTS")
    return hosts


HOSTS = load_hosts(config.HOSTS)
PRIVATE_KEY: Optional[paramiko.PKey] = _parse_private_key(config.SSH_PRIVATE_KEY) if config.SSH_PRIVATE_KEY else None


def get_host(name: str) -> Host:
    """Looks up a host by name. The error lists the available hosts so the agent can correct itself."""
    host = HOSTS.get(name)
    if host is None:
        raise NotFoundError(f"Unknown host '{name}'. Available hosts: {', '.join(HOSTS)}")
    return host
