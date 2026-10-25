from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, List
import shlex
import socket
import paramiko

from shared.logger import get_logger

from .config import config
from .inventory import PRIVATE_KEY, Host


CONNECT_TIMEOUT = 10            # Seconds to establish the SSH connection
COMMAND_TIMEOUT = 60            # Seconds a command may go without producing output
MAX_OUTPUT_BYTES = 64 * 1024


log = get_logger(config.MCP_NAME)


class RemoteError(Exception):
    """Connection or command failure on a remote host. Its message is safe to return to the agent."""
    pass


@dataclass(frozen=True)
class CommandResult:
    exit_status: int
    stdout: str
    stderr: str
    truncated: bool


def _decode(data: bytes) -> tuple[str, bool]:
    truncated = len(data) > MAX_OUTPUT_BYTES
    return data[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), truncated


class Connection:

    def __init__(self, host: Host, client: paramiko.SSHClient):
        self.host = host
        self._client = client

    def run(self, argv: List[str]) -> CommandResult:
        """
        Runs a single command without a PTY. Every argument is quoted, so the remote shell
        only ever sees one command with literal arguments.
        """
        command = shlex.join(argv)
        log.info(f"Running on '{self.host.name}': {command}")
        try:
            stdin, stdout, stderr = self._client.exec_command(command, timeout=COMMAND_TIMEOUT)
            stdin.close()
            out, out_truncated = _decode(stdout.read())
            err, err_truncated = _decode(stderr.read())
            exit_status = stdout.channel.recv_exit_status()
        except (socket.timeout, TimeoutError):
            raise RemoteError(f"Command timed out on host '{self.host.name}'")
        except (paramiko.SSHException, OSError) as e:
            log.warning(f"Command failed on '{self.host.name}': {e!r}")
            raise RemoteError(f"Lost connection to host '{self.host.name}'")
        return CommandResult(exit_status, out, err, out_truncated or err_truncated)

    def run_checked(self, argv: List[str]) -> str:
        """Runs a command and returns its output, raising RemoteError if it exits non-zero."""
        result = self.run(argv)
        if result.exit_status != 0:
            raise RemoteError(
                f"'{argv[0]}' failed on host '{self.host.name}' (exit {result.exit_status}): {result.stderr.strip()}"
            )
        return result.stdout


@contextmanager
def connect(host: Host) -> Iterator[Connection]:
    """Opens an SSH connection to an inventory host, verifying its key against the host_key from the inventory."""
    client = paramiko.SSHClient()
    # Trust only the configured key. Non-standard ports are looked up as '[address]:port', like in known_hosts.
    entry = host.address if host.port == 22 else f"[{host.address}]:{host.port}"
    client.get_host_keys().add(entry, host.host_key.get_name(), host.host_key)
    client.set_missing_host_key_policy(paramiko.RejectPolicy())

    try:
        try:
            client.connect(
                hostname=host.address,
                port=host.port,
                username=host.username,
                password=host.password,
                pkey=None if host.password else PRIVATE_KEY,
                look_for_keys=False,
                allow_agent=False,
                timeout=CONNECT_TIMEOUT,
            )
        except paramiko.BadHostKeyException:
            log.error(f"Host key for '{host.name}' does not match the configured host_key")
            raise RemoteError(f"Host key for '{host.name}' does not match the pinned key. Do not retry; tell the user.")
        except paramiko.AuthenticationException:
            raise RemoteError(f"Authentication to host '{host.name}' failed. Do not retry; tell the user.")
        except paramiko.SSHException as e:
            # RejectPolicy raises a plain SSHException when the server offers a key type other than host_key's
            log.error(f"Could not connect to '{host.name}': {e}")
            if "known_hosts" in str(e):
                raise RemoteError(f"Host '{host.name}' did not offer the configured host key type. Do not retry; tell the user.")
            raise RemoteError(f"Could not connect to host '{host.name}'")
        except (socket.timeout, OSError) as e:
            log.warning(f"Could not connect to '{host.name}': {e!r}")
            raise RemoteError(f"Could not connect to host '{host.name}': unreachable or timed out")

        yield Connection(host, client)
    finally:
        client.close()
