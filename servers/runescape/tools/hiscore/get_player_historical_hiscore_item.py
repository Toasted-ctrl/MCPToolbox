from datetime import datetime, timedelta
from pydantic import Field
from typing import Annotated, Optional
import uuid

from ...config import config
from ...db.schemas import TrackedUsersT, StagingHiscoresT
from ...server import mcp

from shared.db import get_db_session
from shared.errors import NotFoundError


@mcp.tool(
    name="get_player_historical_hiscore_item",
    version="1.0.1",
    meta={
        "author": "Toasted-ctrl"
    },
    description=(
        "Only use this function to fetch historical records for a skill or activity for a tracked player. "
        "If records are stored, a dictionary with the player records will be returned. "
        "The returned dict is based on the first found date FROM the indicated date and time."
    )
)
def get_player_historical_hiscore_item(
    player_name: Annotated[str, Field(description="Name of the RuneScape player.")],
    skill_or_activity: Annotated[str, Field(description="Name of the skill or activity.")] = "Overall",
    date: Annotated[Optional[str], Field(description="Earliest date for which the record needs to be retrieved, example: '2026-05-11' (yyyy-mm-dd).")] = None,
    time: Annotated[Optional[str], Field(description="Earliest time for which the record needs to be retrieved, example: '13:11'.")] = None
) -> dict:
    
    if date is None:
        request_date = datetime(1970, 1, 1)

    elif date is not None:
        date_split = date.split('-')
        year = int(date_split[0])
        month = int(date_split[1])
        day = int(date_split[2])
        request_date = datetime(year, month, day)

    if time is not None:
        time_split = time.split(':')
        hours = int(time_split[0])
        minutes = int(time_split[1])
        request_date = request_date + timedelta(hours=hours, minutes=minutes)
    
    username = player_name.strip().replace(" ", "_")
    
    with get_db_session(db_url=config.DB_URL) as db:
        player_id: uuid.UUID = (
            db.query(TrackedUsersT.id)
            .filter(TrackedUsersT.player_name == username)
            .scalar()
        )
        if player_id is None:
            raise NotFoundError(f"No player found with name '{player_name}'")
        query = (
            db.query(
                StagingHiscoresT.name,
                StagingHiscoresT.ingested_date,
                StagingHiscoresT.rank,
                StagingHiscoresT.level,
                StagingHiscoresT.is_skill,
                StagingHiscoresT.progression_points)
            .filter(
                StagingHiscoresT.user_id == player_id,
                StagingHiscoresT.name == skill_or_activity,
                StagingHiscoresT.ingested_date >= request_date
            )
            .order_by(
                StagingHiscoresT.ingested_date.asc()
            )
            .first()
        )
        if query is None:
            raise NotFoundError(f"No historical records found for '{player_name}' from {request_date}")
        
        return {
            "player_name": player_name,
            "player_hiscore_item": query._asdict()
        }