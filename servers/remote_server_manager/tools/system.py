from pydantic import Field
from typing import Annotated, Literal

from ..inventory import get_host
from ..remote import connect
from ..server import mcp


def _parse_memory(output: str) -> dict:
    # free -b: "Mem:  total used free shared buff/cache available"
    memory = {}
    for line in output.splitlines():
        fields = line.split()
        if fields and fields[0] == "Mem:" and len(fields) >= 7:
            memory.update(total_bytes=int(fields[1]), used_bytes=int(fields[2]), available_bytes=int(fields[6]))
        elif fields and fields[0] == "Swap:" and len(fields) >= 3:
            memory.update(swap_total_bytes=int(fields[1]), swap_used_bytes=int(fields[2]))
    return memory


def _parse_disks(output: str) -> list:
    # df -P -B1: "Filesystem 1-blocks Used Available Capacity Mounted-on", mount points may contain spaces
    disks = []
    for line in output.splitlines()[1:]:
        fields = line.split(maxsplit=5)
        if len(fields) == 6:
            disks.append({
                "filesystem": fields[0],
                "mount": fields[5],
                "size_bytes": int(fields[1]),
                "used_bytes": int(fields[2]),
                "available_bytes": int(fields[3]),
                "use_percent": int(fields[4].rstrip("%")),
            })
    return disks


def _parse_os_name(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip('"')
    return "unknown"


@mcp.tool(
    name="get_system_info",
    version="0.1.0",
    description="Returns an overview of a host: OS, kernel, uptime, load average, memory and disk usage.",
    meta={"author": "Toasted-ctrl"}
)
def get_system_info(
    host: Annotated[str, Field(description="Host name from list_hosts")],
) -> dict:
    with connect(get_host(host)) as conn:
        os_release = conn.run_checked(["cat", "/etc/os-release"])
        kernel = conn.run_checked(["uname", "-srm"]).strip()
        uptime = conn.run_checked(["cat", "/proc/uptime"]).split()
        load = conn.run_checked(["cat", "/proc/loadavg"]).split()
        memory = conn.run_checked(["free", "-b"])
        disks = conn.run_checked(["df", "-P", "-B1", "-x", "tmpfs", "-x", "devtmpfs", "-x", "squashfs", "-x", "overlay"])

    return {
        "host": host,
        "os": _parse_os_name(os_release),
        "kernel": kernel,
        "uptime_seconds": int(float(uptime[0])),
        "load_average": {"1m": float(load[0]), "5m": float(load[1]), "15m": float(load[2])},
        "memory": _parse_memory(memory),
        "disks": _parse_disks(disks),
    }


@mcp.tool(
    name="list_processes",
    version="0.1.0",
    description="Lists the top processes on a host by CPU or memory usage.",
    meta={"author": "Toasted-ctrl"}
)
def list_processes(
    host: Annotated[str, Field(description="Host name from list_hosts")],
    sort_by: Annotated[Literal["cpu", "memory"], Field(description="Sort by CPU or memory usage")] = "cpu",
    limit: Annotated[int, Field(description="Number of processes to return", ge=1, le=50)] = 15,
) -> dict:
    sort_key = "-pcpu" if sort_by == "cpu" else "-pmem"
    with connect(get_host(host)) as conn:
        output = conn.run_checked(["ps", "-eo", "pid=,user=,pcpu=,pmem=,etimes=,comm=", f"--sort={sort_key}"])

    processes = []
    for line in output.splitlines()[:limit]:
        fields = line.split(maxsplit=5)
        if len(fields) == 6:
            processes.append({
                "pid": int(fields[0]),
                "user": fields[1],
                "cpu_percent": float(fields[2]),
                "memory_percent": float(fields[3]),
                "elapsed_seconds": int(fields[4]),
                "command": fields[5],
            })
    return {"host": host, "sort_by": sort_by, "processes": processes}