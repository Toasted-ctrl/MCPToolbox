from typing import Annotated

import requests
from pydantic import Field

from ...config import config
from ...server import mcp


@mcp.tool(
    name="get_grand_exchange_item",
    version="1.0.2",
    meta={"author": "Toasted-ctrl"},
    description=(
        "Retrieves Grand Exhange information for an item that can be sold on the Grand Exchange. "
        "Only use this tool when the user is asking for sales data with an item id, or asking for Grand Exchange data on an item id. "
        "If the user does not specify an item id, you may ask for one. "
        "Do NOT use this tool for hiscore related queries. "
        "Returns a dictionary which includes: "
        "item type, item id, item name, item description, item member status, pricing trends: (current, today, day30, day90, day180)."
    ),
)
def get_grand_exchange_item(
    item_id: Annotated[
        int, Field(description="Integer representing the id of the item.")
    ],
) -> dict:
    if not item_id:
        raise ValueError("Missing item_id")
    url = config.RS_GE_LINK
    params = {"item": int(item_id)}
    response = requests.get(url=url, params=params)
    response.raise_for_status()
    return response.json().get("item")
