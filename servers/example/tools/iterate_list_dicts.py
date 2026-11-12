from typing import Annotated

from pydantic import BaseModel, Field

from ..server import mcp

# NOTE: Example tool where we iterate through a list of dictionaries, and return the dictionaries.
# NOTE: Using a pydantic model we can also control which criteria each Item within the list must meet.


class Item(BaseModel):
    name: str = Field(description="Name of the item")
    property: str = Field(description="Property of the item")
    description: str = Field(description="Description of the item")


@mcp.tool(
    name="iterate_list_dicts",
    version="1.0.0",
    description="Ingest and iterate several dictionaries in a list and return them.",
    meta={"author": "Toasted-ctrl"},
)
def iterate_list_dicts(
    items: Annotated[list[Item], Field(description="List of items")],
) -> dict:
    if not items:
        raise ValueError("At least one item must be provided")
    return {"result": [item.model_dump() for item in items]}
