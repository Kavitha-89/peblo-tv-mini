from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Show(Base):
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    section = Column(String(50))
    status = Column(String(20), default="draft", nullable=False)

    seasons = relationship(
        "Season",
        back_populates="show",
        cascade="all, delete-orphan",
    )

    categories = relationship(
        "ShowCategory",
        back_populates="show",
        cascade="all, delete-orphan",
    )

    artwork = relationship(
        "Artwork",
        back_populates="show",
        cascade="all, delete-orphan",
    )


class ShowCategory(Base):
    __tablename__ = "show_categories"

    id = Column(Integer, primary_key=True, index=True)

    show_id = Column(
        Integer,
        ForeignKey("shows.id"),
        nullable=False,
    )

    category = Column(
        String(100),
        nullable=False,
    )

    show = relationship(
        "Show",
        back_populates="categories",
    )

    __table_args__ = (
        UniqueConstraint(
            "show_id",
            "category",
            name="uq_show_category",
        ),
    )


class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, index=True)

    show_id = Column(
        Integer,
        ForeignKey("shows.id"),
        nullable=False,
    )

    season_number = Column(
        Integer,
        nullable=False,
    )

    title = Column(String(255))

    show = relationship(
        "Show",
        back_populates="seasons",
    )

    episodes = relationship(
        "Episode",
        back_populates="season",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "show_id",
            "season_number",
            name="uq_show_season_number",
        ),
    )


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(Integer, primary_key=True, index=True)

    seed_episode_id = Column(
        String(100),
        unique=True,
        index=True,
    )

    season_id = Column(
        Integer,
        ForeignKey("seasons.id"),
        nullable=False,
    )

    episode_number = Column(
        Integer,
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=False,
    )

    description = Column(Text)

    duration = Column(Integer)

    language = Column(
        String(10),
        nullable=False,
    )

    content_group = Column(
        String(255),
        nullable=False,
    )

    status = Column(
        String(20),
        default="draft",
        nullable=False,
    )

    season = relationship(
        "Season",
        back_populates="episodes",
    )

    artwork = relationship(
        "Artwork",
        back_populates="episode",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "content_group",
            "language",
            name="uq_episode_content_group_language",
        ),
    )


class Artwork(Base):
    __tablename__ = "artwork"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    episode_id = Column(
        Integer,
        ForeignKey("episodes.id"),
        nullable=True,
    )

    show_id = Column(
        Integer,
        ForeignKey("shows.id"),
        nullable=True,
    )

    artwork_type = Column(
        String(20),
        nullable=False,
    )

    file_path = Column(
        String(500),
        nullable=False,
    )

    width = Column(
        Integer,
        nullable=False,
    )

    height = Column(
        Integer,
        nullable=False,
    )

    file_size = Column(
        Integer,
        nullable=False,
    )

    episode = relationship(
        "Episode",
        back_populates="artwork",
    )

    show = relationship(
        "Show",
        back_populates="artwork",
    )

    __table_args__ = (
        UniqueConstraint(
            "episode_id",
            "artwork_type",
            name="uq_episode_artwork_type",
        ),
        UniqueConstraint(
            "show_id",
            "artwork_type",
            name="uq_show_artwork_type",
        ),
    )


class PublishRun(Base):
    __tablename__ = "publish_runs"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    published_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    published_by = Column(
        String(255),
        nullable=False,
    )

    shows_count = Column(
        Integer,
        default=0,
        nullable=False,
    )

    episodes_count = Column(
        Integer,
        default=0,
        nullable=False,
    )

    outcome = Column(
        String(30),
        nullable=False,
    )

    error_message = Column(Text)


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    issue_type = Column(
        String(30),
        nullable=False,
    )

    entity = Column(
        String(30),
        nullable=False,
    )

    seed_episode_id = Column(
        String(100),
    )

    message = Column(
        Text,
        nullable=False,
    )

    resolved = Column(
        String(20),
        default="open",
        nullable=False,
    )