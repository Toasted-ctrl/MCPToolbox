from pathlib import Path
from typing import Annotated

from pydantic import Field

from ..server import mcp


@mcp.tool(
    name="list_files",
    version="0.0.1",
    description="lists files in provided directory",
    meta={"author": "Toasted-ctrl"},
)
def list_files(
    directory: Annotated[str, Field(description="Directory path")] = ".",
) -> dict[str, list[dict]]:

    # NOTE: Stat module originates from Unix - stat -> get file status.

    return {
        "result": [
            {"name": str(f), "size": f"{f.stat().st_size} bytes"}
            for f in Path(directory).iterdir()
        ]
    }
