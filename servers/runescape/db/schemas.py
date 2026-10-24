import uuid
from datetime import datetime
from sqlalchemy import String, text, UUID, Boolean, Integer, BigInteger, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TrackedUsersT(Base):
    __tablename__ = 'tracked_users'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )

    player_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    inserted_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )

    inserted_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default=text("current_user")
    )

    is_tracked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true")
    )


class StagingHiscoresT(Base):
    __tablename__ = 'staging_hiscores'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        nullable=False
    )

    ingested_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False
    )

    inserted_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now()")
    )

    inserted_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default=text("current_user")
    )

    is_skill: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    progression: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    # We need BIGINT here as max total XP may exceed the 2.1B threshold.
    progression_points: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    level: Mapped[int] = mapped_column(
        Integer,
        nullable=True
    )

    rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )