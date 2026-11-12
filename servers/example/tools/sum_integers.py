from typing import Annotated

from pydantic import Field

from ..server import mcp

# NOTE: Example tool where one iterates through and sums a list of integers.


@mcp.tool(
    name="sum_integers",
    version="1.0.0",
    description=("Sums a list of integers"),
    meta={"author": "Toasted-ctrl"},
)
def sum_integers(
    integers: Annotated[list[int], Field(description="List of integers")],
) -> dict:
    if len(integers) < 2:
        raise ValueError("At least two integers must be provided.")
    return {"result": sum(integers)}
