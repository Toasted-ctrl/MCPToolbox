from typing import Annotated

from pydantic import Field

from shared.db import get_db_session
from shared.errors import NotFoundError

from ...config import config
from ...db.schemas import TrackedUsersT
from ...server import mcp


@mcp.tool(
    name="disable_player_tracking",
    version="1.0.1",
    meta={"author": "Toasted-ctrl"},
    description=(
        "This function disables tracking for a RuneScape player, if the player is CURRENTLY actively being tracked. "
        "Returns the player_name if tracking was successfully disabled. "
        "Will return an error if the player's tracking is already disabled, "
        "or if the player does not exist in the tracking database."
    ),
)
def disable_player_tracking(
    player_name: Annotated[str, Field(description="Name of the RuneScape player.")],
) -> dict[str, str]:
    """Disables tracking for a tracked player.
    Note that this does NOT REMOVE them from the database, so we can keep the original ids in place.
    Return ths username if updates successfully."""

    with get_db_session(db_url=config.DB_URL) as db:
        tp: TrackedUsersT | None = (
            db.query(TrackedUsersT)
            .filter(
                TrackedUsersT.player_name == player_name,
                TrackedUsersT.is_tracked.is_(True),
            )
            .one_or_none()
        )
        if not tp:
            raise NotFoundError(f"No tracking active for '{player_name}'")
        tp.is_tracked = False
        db.commit()
        return {"disabled_tracking": tp.player_name}
