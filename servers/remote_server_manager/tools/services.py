from pydantic import Field
from typing import Annotated, Literal, Optional

from shared.errors import NotFoundError

from ..inventory import get_host, normalize_service
from ..remote import RemoteError, connect
from ..server import mcp


_STATUS_PROPERTIES = (
    "Id", "Description", "LoadState", "ActiveState", "SubState", "UnitFileState",
    "MainPID", "ActiveEnterTimestamp", "NRestarts", "Result",
)


@mcp.tool(
    name="list_services",
    version="0.1.0",
    description="Lists systemd services on a host, filtered by state.",
    meta={"author": "Toasted-ctrl"}
)
def list_services(
    host: Annotated[str, Field(description="Host name from list_hosts")],
    state: Annotated[Literal["running", "failed", "all"], Field(description="Which services to list")] = "running",
) -> dict:
    argv = ["systemctl", "list-units", "--type=service", "--no-legend", "--plain", "--no-pager"]
    argv.append("--all" if state == "all" else f"--state={state}")

    with connect(get_host(host)) as conn:
        output = conn.run_checked(argv)

    services = []
    for line in output.splitlines():
        fields = line.split(maxsplit=4)
        if len(fields) >= 4:
            services.append({
                "unit": fields[0],
                "load": fields[1],
                "active": fields[2],
                "sub": fields[3],
                "description": fields[4] if len(fields) == 5 else "",
            })
    return {"host": host, "state": state, "services": services}


@mcp.tool(
    name="get_service_status",
    version="0.1.0",
    description="Returns the status of a systemd service on a host: active state, enabled state, main PID, restarts.",
    meta={"author": "Toasted-ctrl"}
)
def get_service_status(
    host: Annotated[str, Field(description="Host name from list_hosts")],
    service: Annotated[str, Field(description="Service name, e.g. 'nginx' or 'nginx.service'")],
) -> dict:
    unit = normalize_service(service)
    with connect(get_host(host)) as conn:
        output = conn.run_checked(["systemctl", "show", "--no-pager", f"--property={','.join(_STATUS_PROPERTIES)}", "--", unit])

    status = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    if status.get("LoadState") == "not-found":
        raise NotFoundError(f"Service '{unit}' not found on host '{host}'")
    return {"host": host, **status}


@mcp.tool(
    name="read_service_logs",
    version="0.1.0",
    description="Reads the most recent journal entries of a systemd service on a host.",
    meta={"author": "Toasted-ctrl"}
)
def read_service_logs(
    host: Annotated[str, Field(description="Host name from list_hosts")],
    service: Annotated[str, Field(description="Service name, e.g. 'nginx' or 'nginx.service'")],
    lines: Annotated[int, Field(description="Number of most recent entries to return", ge=1, le=500)] = 100,
    priority: Annotated[
        Optional[Literal["emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"]],
        Field(description="Only return entries of this priority or more severe"),
    ] = None,
) -> dict:
    unit = normalize_service(service)
    argv = ["journalctl", "--no-pager", "--output=short-iso", f"--lines={lines}", f"--unit={unit}"]
    if priority:
        argv.append(f"--priority={priority}")

    with connect(get_host(host)) as conn:
        result = conn.run(argv)

    if result.exit_status != 0:
        raise RemoteError(f"Could not read logs on host '{host}' (exit {result.exit_status}): {result.stderr.strip()}")
    return {"host": host, "service": unit, "logs": result.stdout, "truncated": result.truncated}


@mcp.tool(
    name="restart_service",
    version="0.1.0",
    description="Restarts a systemd service on a host. Only services listed for the host in list_hosts can be restarted.",
    meta={"author": "Toasted-ctrl"}
)
def restart_service(
    host: Annotated[str, Field(description="Host name from list_hosts")],
    service: Annotated[str, Field(description="Service name, e.g. 'nginx' or 'nginx.service'")],
) -> dict:
    target = get_host(host)
    unit = normalize_service(service)
    if unit not in target.restartable_services:
        raise ValueError(
            f"Service '{unit}' may not be restarted on host '{host}'. "
            f"Do not retry; ask the user to add it to restartable_services if this is needed."
        )

    argv = ["systemctl", "restart", "--", unit]
    if target.sudo:
        argv = ["sudo", "-n"] + argv

    with connect(target) as conn:
        result = conn.run(argv)
        if result.exit_status != 0:
            raise RemoteError(f"Restart of '{unit}' on host '{host}' failed (exit {result.exit_status}): {result.stderr.strip()}")
        active_state = conn.run(["systemctl", "is-active", "--", unit]).stdout.strip()

    return {"host": host, "service": unit, "status": "restarted", "active_state": active_state}
