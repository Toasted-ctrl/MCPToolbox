from typing import Annotated

import requests
from pydantic import Field

from ...config import config
from ...server import mcp


def _unpack_hiscore_item(type: str, listing: list[str]) -> dict[str, str | None]:
    """Unpacks a hiscore item."""

    item: dict[str, str | None] = {}
    if type == "skill":
        item["type"] = "skill"
        item["ranking"] = listing[0]
        item["level"] = listing[1]
        item["exp_score"] = listing[2]
    if type == "activity":
        item["type"] = "activity"
        item["ranking"] = listing[0]
        item["level"] = None
        item["exp_score"] = listing[1]
    return item


def _unpack_hiscore(input: str) -> dict[str, dict[str, str | None]]:
    """Unpacks the hiscore body of text returned from the RuneScape hiscore API."""

    hiscore_items: list = [
        "Overall",
        "Attack",
        "Defence",
        "Strength",
        "Constitution",
        "Ranged",
        "Prayer",
        "Magic",
        "Cooking",
        "Woodcutting",
        "Fletching",
        "Fishing",
        "Firemaking",
        "Crafting",
        "Smithing",
        "Mining",
        "Herblore",
        "Agility",
        "Thieving",
        "Slayer",
        "Farming",
        "Runecrafting",
        "Hunting",
        "Construction",
        "Summoning",
        "Dungeoneering",
        "Divination",
        "Invention",
        "Archaeology",
        "Necromancy",
        "Bounty Hunter",
        "B.H. Rogues",
        "Dominion Tower",
        "The Crucible",
        "Castle Wars games",
        "B.A. Attackers",
        "B.A. Defenders",
        "B.A. Collectors",
        "B.A. Healers",
        "Duel Tournament",
        "Mobilising Armies",
        "Conquest",
        "Fist of Guthix",
        "GG: Athletics",
        "GG: Resource Race",
        "WE2: Armadyl Lifetime Contribution",
        "WE2: Bandos Lifetime Contribution",
        "WE2: Armadyl PvP kills",
        "WE2: Bandos PvP kills",
        "Heist Guard Level",
        "Heist Robber Level",
        "CFP: 5 game average",
        "AF15: Cow Tipping",
        "AF15: Rats killed after the miniquest",
        "RuneScore",
        "Clue Scrolls Easy",
        "Clue Scrolls Medium",
        "Clue Scrolls Hard",
        "Clue Scrolls Elite",
        "Clue Scrolls Master",
        "League Points",
    ]

    hiscores = {}
    listings = input.split("\n")

    for idx, line in enumerate(listings):
        listing = line.split(",")
        if idx < 30:
            hiscores[hiscore_items[idx]] = _unpack_hiscore_item(
                type="skill", listing=listing
            )

        elif idx > 29 and idx < 61:
            hiscores[hiscore_items[idx]] = _unpack_hiscore_item(
                type="activity", listing=listing
            )

    return hiscores


@mcp.tool(
    name="get_player_current_hiscore",
    version="1.0.2",
    meta={"author": "Toasted-ctrl"},
    description=(
        "Retrieves and returns the current hiscore listings for the specified RuneScape player. "
        "Only use this tool when the user is asking for the hiscores or stats of a RuneScape player. "
        "Do NOT use this tool if the user asks any other question. "
        "Returns a dictionary of stats / hiscores related to the specified RuneScape player."
    ),
)
def get_player_current_hiscore(
    player_name: Annotated[str, Field(description="Name of the RuneScape player.")],
) -> dict:
    if not player_name:
        raise ValueError("Player name must not be None")
    url = config.RS_HS_LINK
    params = {"player": player_name}
    response = requests.get(url=url, params=params)
    response.raise_for_status()
    return {
        "player_name": player_name,
        "player_hiscores": _unpack_hiscore(input=str(response.text)),
    }
