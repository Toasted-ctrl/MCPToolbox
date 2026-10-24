from pydantic import Field
from typing import Annotated, Dict, Optional
import paramiko
import uuid
import threading
import time

from ..server import mcp


# Session storage: {session_id: {'client': client, 'stdin': stdin, 'stdout': stdout, 'stderr': stderr}}
_ssh_sessions: Dict[str, dict] = {}
_session_lock = threading.Lock()


def _read_available(stdout, stderr, timeout: float = 0.5) -> str:
    """Read all currently buffered data from stdout and stderr."""
    output = ""
    start = time.time()

    while time.time() - start < timeout:
        try:
            # Read stdout - ChannelFile objects have recv_ready() and recv()
            if stdout.channel.recv_ready():
                data = stdout.channel.recv(4096)
                output += data.decode('utf-8', errors='replace')

            # Read stderr
            if stderr.channel.recv_ready():
                data = stderr.channel.recv(4096)
                output += data.decode('utf-8', errors='replace')

            time.sleep(0.05)
        except Exception:
            break

    return output


def _cleanup_session(session_id: str):
    """Safely remove and close a session."""
    with _session_lock:
        session = _ssh_sessions.pop(session_id, None)
    
    if session:
        try:
            session['stdin'].close()
            session['stdout'].close()
            session['stderr'].close()
            session['client'].close()
        except Exception:
            pass


@mcp.tool(
    name="create_ssh_session",
    version="0.0.1",
    description="Creates a persistent SSH shell session with PTY allocation. Returns a session_id that can be used to send commands and read output.",
    meta={"author": "Toasted-ctrl"}
)
def create_ssh_session(
    server_name: Annotated[str, Field(description="Server hostname or IP address")],
    username: Annotated[str, Field(description="SSH username")],
    password: Annotated[Optional[str], Field(description="SSH password (optional, uses keys if not provided)")] = None,
    port: Annotated[int, Field(description="SSH port", default=22)] = 22,
    shell: Annotated[str, Field(description="Shell to invoke", default="/bin/bash")] = "/bin/bash",
    timeout: Annotated[int, Field(description="Connection timeout in seconds", default=10)] = 10,
) -> dict:
    """
    Creates a persistent interactive shell session with proper terminal emulation.
    
    The PTY (pseudo-terminal) allocation ensures:
    - Proper terminal behavior (colors, line editing, etc.)
    - Programs that require a TTY (sudo, editors, etc.) work correctly
    - Better interaction with interactive commands
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=server_name,
            username=username,
            password=password,
            port=port,
            look_for_keys=True,
            timeout=timeout
        )

        # Create shell with PTY - this is the key difference from invoke_shell()
        stdin, stdout, stderr = client.exec_command(
            shell,
            get_pty=True,  # Allocate a pseudo-terminal
            timeout=timeout
        )

        session_id = str(uuid.uuid4())

        with _session_lock:
            _ssh_sessions[session_id] = {
                'client': client,
                'stdin': stdin,
                'stdout': stdout,
                'stderr': stderr,
                'server': server_name,
                'username': username,
                'shell': shell,
                'created_at': time.time(),
                'last_activity': time.time()
            }

        # Wait for initial shell prompt
        time.sleep(0.5)
        initial_output = _read_available(stdout, stderr, timeout=1.0)

        return {
            "session_id": session_id,
            "server": server_name,
            "username": username,
            "shell": shell,
            "initial_output": initial_output,
            "status": "connected"
        }

    except Exception as e:
        try:
            client.close()
        except:
            pass
        raise Exception(f"Failed to create SSH session: {str(e)}")


@mcp.tool(
    name="send_to_ssh_session",
    version="0.0.1",
    description="Sends a command or input to an existing SSH session.",
    meta={"author": "Toasted-ctrl"}
)
def send_to_ssh_session(
    session_id: Annotated[str, Field(description="Session ID from create_ssh_session")],
    input: Annotated[str, Field(description="Command or text to send (newline will be added automatically)")],
) -> dict:
    """
    Sends input to the session. Automatically appends a newline.
    For multi-line commands, include \n in your input string.
    """
    with _session_lock:
        session = _ssh_sessions.get(session_id)

    if not session:
        raise Exception(f"Session {session_id} not found")

    try:
        # Send input with newline - ChannelStdinFile uses write(), not send()
        session['stdin'].write(input + "\n")
        session['stdin'].flush()
        session['last_activity'] = time.time()
        return {"session_id": session_id, "status": "input_sent"}
    except Exception as e:
        _cleanup_session(session_id)
        raise Exception(f"Failed to send input: {str(e)}")


@mcp.tool(
    name="read_from_ssh_session",
    version="0.0.1",
    description="Reads output from an SSH session. Can be called multiple times to get incremental output.",
    meta={"author": "Toasted-ctrl"}
)
def read_from_ssh_session(
    session_id: Annotated[str, Field(description="Session ID from create_ssh_session")],
    timeout: Annotated[float, Field(description="Maximum time to wait for output in seconds", default=2.0)] = 2.0,
) -> dict:
    """
    Reads available output from the session.
    
    Call this after send_to_ssh_session to retrieve command output.
    For long-running commands, you may need to call this multiple times.
    """
    with _session_lock:
        session = _ssh_sessions.get(session_id)

    if not session:
        raise Exception(f"Session {session_id} not found")

    try:
        output = _read_available(session['stdout'], session['stderr'], timeout)
        session['last_activity'] = time.time()

        # Check if the shell process has exited
        is_closed = False
        if hasattr(session['stdout'], 'channel'):
            is_closed = session['stdout'].channel.exit_status_ready()

        return {
            "session_id": session_id,
            "output": output,
            "has_more": len(output) > 0,  # Simple indicator that we got data
            "closed": is_closed
        }
    except Exception as e:
        _cleanup_session(session_id)
        raise Exception(f"Failed to read output: {str(e)}")


@mcp.tool(
    name="list_ssh_sessions",
    version="0.0.1",
    description="Lists all active SSH sessions with their details.",
    meta={"author": "Toasted-ctrl"}
)
def list_ssh_sessions() -> dict:
    """
    Returns information about all currently active SSH sessions.
    Useful for checking what sessions are open and their status.
    """
    with _session_lock:
        sessions = []
        for session_id, session in _ssh_sessions.items():
            # Check if the session is still alive
            is_alive = True
            exit_status = None
            
            try:
                if hasattr(session['stdout'], 'channel'):
                    is_alive = not session['stdout'].channel.exit_status_ready()
                    exit_status = session['stdout'].channel.get_exit_status()
            except Exception:
                is_alive = False
            
            sessions.append({
                "session_id": session_id,
                "server": session.get('server', 'unknown'),
                "username": session.get('username', 'unknown'),
                "shell": session.get('shell', 'unknown'),
                "created_at": session.get('created_at', 0),
                "last_activity": session.get('last_activity', 0),
                "is_alive": is_alive,
                "exit_status": exit_status
            })
        
        return {
            "sessions": sessions,
            "count": len(sessions)
        }


@mcp.tool(
    name="close_ssh_session",
    version="0.0.1",
    description="Closes and removes an SSH session.",
    meta={"author": "Toasted-ctrl"}
)
def close_ssh_session(
    session_id: Annotated[str, Field(description="Session ID to close")]
) -> dict:
    """Terminates the SSH session and removes it from memory."""
    _cleanup_session(session_id)
    return {"session_id": session_id, "status": "closed"}
