from typing import Annotated

from pydantic import Field

from shared.db import get_db_session

from ...config import config
from ...db.schemas import TrackedUsersT
from ...server import mcp


@mcp.tool(
    name="post_tracked_user",
    version="0.1.1",
    meta={"author": "Toasted-ctrl"},
    description=(
        "Adds a new user / username / player_name for which hiscores / stats / runemetrics profiles need to be tracked. "
        "Only use this tool when the user is requesting to add tracking a player / user. "
        "Returns the player_name if added successfully."
    ),
)
def post_tracked_user(
    player_name: Annotated[str, Field(description="Name of the RuneScape player.")],
) -> dict[str, str]:
    """Processes new user to be tracked. Returns the username if added successfully."""

    with get_db_session(db_url=config.DB_URL) as db:
        tp: TrackedUsersT = (
            db.query(TrackedUsersT)
            .filter(TrackedUsersT.player_name == player_name)
            .scalar()
        )
        if not tp:
            ntp = TrackedUsersT(is_tracked=True, player_name=player_name)
            db.add(ntp)
            db.commit()
            return {"tracking_enabled": ntp.player_name}
        if not tp.is_tracked:
            tp.is_tracked = True
            db.commit()
            return {"tracking_enabled": tp.player_name}
        raise ValueError(f"'{player_name}' is already tracked")
