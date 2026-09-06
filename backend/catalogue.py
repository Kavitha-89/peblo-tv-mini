import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models import Show, Season, Episode, Artwork


BASE_DIR = Path(__file__).resolve().parent
CATALOGUE_FILE = BASE_DIR / "catalogue.json"
TEMP_CATALOGUE_FILE = BASE_DIR / "catalogue.json.tmp"


SECTION_ORDER = {
    "featured": 1,
    "series": 2,
    "minisodes": 3,
    "songs": 4,
}


def artwork_url(file_path: str | None) -> str | None:
    """
    Convert the internal Windows/local storage path into
    a URL that the viewer can use.
    """
    if not file_path:
        return None

    normalized = file_path.replace("\\", "/")

    if normalized.startswith("assets/"):
        return "/" + normalized

    return "/" + normalized


def get_artwork(episode: Episode, artwork_type: str) -> str | None:
    """
    Return the URL for a specific artwork type.
    """
    for artwork in episode.artwork:
        if artwork.artwork_type == artwork_type:
            return artwork_url(artwork.file_path)

    return None


def get_show_banner(show: Show) -> str | None:
    """
    Prefer show-level banner artwork.

    If unavailable, fall back to the first published episode
    that has a banner.
    """
    for artwork in show.artwork:
        if artwork.artwork_type == "banner":
            return artwork_url(artwork.file_path)

    episodes = []

    for season in show.seasons:
        if season.season_number == 0:
            continue

        for episode in season.episodes:
            if episode.status == "published":
                episodes.append(episode)

    episodes.sort(key=lambda ep: (ep.episode_number, ep.id))

    for episode in episodes:
        banner = get_artwork(episode, "banner")
        if banner:
            return banner

    return None


def get_show_poster(show: Show) -> str | None:
    """
    Prefer show-level poster artwork.

    If unavailable, fall back to the first published episode
    poster.
    """
    for artwork in show.artwork:
        if artwork.artwork_type == "poster":
            return artwork_url(artwork.file_path)

    episodes = []

    for season in show.seasons:
        if season.season_number == 0:
            continue

        for episode in season.episodes:
            if episode.status == "published":
                episodes.append(episode)

    episodes.sort(key=lambda ep: (ep.episode_number, ep.id))

    for episode in episodes:
        poster = get_artwork(episode, "poster")
        if poster:
            return poster

    return None


def build_catalogue(db: Session) -> dict[str, Any]:
    """
    Build the complete viewer catalogue.

    Only published shows and published episodes are included.

    Episodes sharing the same content_group are collapsed
    into one catalogue episode with a languages list.
    """

    shows = (
        db.query(Show)
        .filter(Show.status == "published")
        .all()
    )

    # Only shows with valid sections can appear in the catalogue.
    shows = [
        show
        for show in shows
        if show.section in SECTION_ORDER
    ]

    shows.sort(
        key=lambda show: (
            SECTION_ORDER.get(show.section, 999),
            show.title.lower(),
            show.id,
        )
    )

    catalogue_shows = []

    for show in shows:
        seasons_output = []

        seasons = [
            season
            for season in show.seasons
            if season.season_number != 0
        ]

        seasons.sort(key=lambda season: season.season_number)

        for season in seasons:
            published_episodes = [
                episode
                for episode in season.episodes
                if episode.status == "published"
            ]

            # Group language variants by content_group.
            grouped: dict[str, list[Episode]] = {}

            for episode in published_episodes:
                grouped.setdefault(
                    episode.content_group,
                    []
                ).append(episode)

            grouped_episodes = []

            for content_group, variants in grouped.items():
                variants.sort(
                    key=lambda episode: (
                        0 if episode.language == "en" else 1,
                        episode.language,
                        episode.id,
                    )
                )

                canonical = variants[0]

                languages = sorted(
                    {
                        episode.language
                        for episode in variants
                    }
                )

                language_variants = []

                for variant in variants:
                    language_variants.append(
                        {
                            "language": variant.language,
                            "title": variant.title,
                            "duration_seconds": variant.duration,
                            "artwork": {
                                "poster": get_artwork(
                                    variant,
                                    "poster",
                                ),
                                "thumbnail": get_artwork(
                                    variant,
                                    "thumbnail",
                                ),
                                "banner": get_artwork(
                                    variant,
                                    "banner",
                                ),
                            },
                        }
                    )

                grouped_episodes.append(
                    {
                        "content_group": content_group,
                        "episode_number": canonical.episode_number,
                        "title": canonical.title,
                        "description": canonical.description,
                        "duration_seconds": canonical.duration,
                        "languages": languages,
                        "artwork": {
                            "poster": get_artwork(
                                canonical,
                                "poster",
                            ),
                            "thumbnail": get_artwork(
                                canonical,
                                "thumbnail",
                            ),
                            "banner": get_artwork(
                                canonical,
                                "banner",
                            ),
                        },
                        "variants": language_variants,
                    }
                )

            grouped_episodes.sort(
                key=lambda episode: (
                    episode["episode_number"],
                    episode["content_group"],
                )
            )

            if grouped_episodes:
                seasons_output.append(
                    {
                        "season_number": season.season_number,
                        "title": season.title,
                        "episodes": grouped_episodes,
                    }
                )

        categories = sorted(
            category.category
            for category in show.categories
        )

        catalogue_shows.append(
            {
                "id": show.id,
                "slug": show.slug,
                "title": show.title,
                "description": show.description,
                "section": show.section,
                "categories": categories,
                "artwork": {
                    "poster": get_show_poster(show),
                    "banner": get_show_banner(show),
                },
                "seasons": seasons_output,
            }
        )

    return {
        "version": 1,
        "shows": catalogue_shows,
    }


def write_catalogue_atomically(catalogue: dict[str, Any]) -> None:
    """
    Write catalogue.json safely.

    The catalogue is first written to a temporary file.
    os.replace() then swaps it into place atomically.
    """

    TEMP_CATALOGUE_FILE.write_text(
        json.dumps(
            catalogue,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    os.replace(
        TEMP_CATALOGUE_FILE,
        CATALOGUE_FILE,
    )


def read_catalogue() -> dict[str, Any]:
    """
    Read the currently published catalogue.
    """

    if not CATALOGUE_FILE.exists():
        return {
            "version": 1,
            "shows": [],
        }

    with CATALOGUE_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)