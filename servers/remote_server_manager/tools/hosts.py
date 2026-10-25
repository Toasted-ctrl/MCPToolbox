from ..inventory import HOSTS
from ..server import mcp


@mcp.tool(
    name="list_hosts",
    version="0.1.0",
    description="Lists the hosts that can be managed, and which services may be restarted on each.",
    meta={"author": "Toasted-ctrl"}
)
def list_hosts() -> dict:
    """Addresses and credentials are deliberately left out; tools only take the host name."""
    return {
        "hosts": [
            {"name": host.name, "restartable_services": list(host.restartable_services)}
            for host in HOSTS.values()
        ]
    }
