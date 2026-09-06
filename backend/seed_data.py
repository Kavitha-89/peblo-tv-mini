import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Show,
    ShowCategory,
    Season,
    Episode,
    Artwork,
    ValidationIssue,
)


DATABASE_URL = "postgresql://peblo:peblo123@localhost:5433/peblo_tv"

BASE_DIR = Path(__file__).resolve().parent
SEED_FILE = BASE_DIR / "seed_shows.json"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def load_seed_data():
    with open(SEED_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def seed_database():
    data = load_seed_data()
    db = SessionLocal()

    try:
        show_map = {}
        season_map = {}

        imported_episodes = 0
        skipped_episodes = 0
        duplicate_issues_added = 0

        for row in data:
            slug = row["slug"]

            # ---------------------------------------------------------
            # 1. Find or create show
            # ---------------------------------------------------------
            show = show_map.get(slug)

            if show is None:
                show = (
                    db.query(Show)
                    .filter(Show.slug == slug)
                    .first()
                )

            if show is None:
                show = Show(
                    slug=slug,
                    title=row["show_title"],
                    description=row["synopsis"],
                    section=row["section"],
                    status=row["status"],
                )

                db.add(show)
                db.flush()

                for category in row.get("categories", []):
                    existing_category = (
                        db.query(ShowCategory)
                        .filter(
                            ShowCategory.show_id == show.id,
                            ShowCategory.category == category,
                        )
                        .first()
                    )

                    if existing_category is None:
                        db.add(
                            ShowCategory(
                                show_id=show.id,
                                category=category,
                            )
                        )

                show_map[slug] = show

            # ---------------------------------------------------------
            # 2. Find or create season
            # ---------------------------------------------------------
            season_number = row["season_number"]
            season_key = (show.id, season_number)

            season = season_map.get(season_key)

            if season is None:
                season = (
                    db.query(Season)
                    .filter(
                        Season.show_id == show.id,
                        Season.season_number == season_number,
                    )
                    .first()
                )

            if season is None:
                season = Season(
                    show_id=show.id,
                    season_number=season_number,
                    title=f"Season {season_number}",
                )

                db.add(season)
                db.flush()

                season_map[season_key] = season

            # ---------------------------------------------------------
            # 3. Check whether this exact seed episode already exists
            # ---------------------------------------------------------
            existing_seed_episode = (
                db.query(Episode)
                .filter(
                    Episode.seed_episode_id == row["episode_id"]
                )
                .first()
            )

            if existing_seed_episode is not None:
                skipped_episodes += 1

                print(
                    f"SKIPPED EXISTING EPISODE: "
                    f"{row['episode_id']}"
                )

                continue

            # ---------------------------------------------------------
            # 4. Check content_group + language uniqueness
            # ---------------------------------------------------------
            existing_episode = (
                db.query(Episode)
                .filter(
                    Episode.content_group == row["content_group"],
                    Episode.language == row["language"],
                )
                .first()
            )

            if existing_episode is not None:
                skipped_episodes += 1

                print(
                    f"SKIPPED DUPLICATE: "
                    f"{row['episode_id']} | "
                    f"{row['content_group']} | "
                    f"{row['language']}"
                )

                # Add the validation issue only if the same issue
                # has not already been recorded.
                existing_issue = (
                    db.query(ValidationIssue)
                    .filter(
                        ValidationIssue.seed_episode_id
                        == row["episode_id"],
                        ValidationIssue.message
                        == (
                            "Duplicate content_group + language: "
                            f"{row['content_group']} + "
                            f"{row['language']}"
                        ),
                        ValidationIssue.resolved == "open",
                    )
                    .first()
                )

                if existing_issue is None:
                    issue = ValidationIssue(
                        issue_type="blocking",
                        entity="episode",
                        seed_episode_id=row["episode_id"],
                        message=(
                            "Duplicate content_group + language: "
                            f"{row['content_group']} + "
                            f"{row['language']}"
                        ),
                        resolved="open",
                    )

                    db.add(issue)
                    duplicate_issues_added += 1

                continue

            # ---------------------------------------------------------
            # 5. Create episode
            # ---------------------------------------------------------
            episode = Episode(
                seed_episode_id=row["episode_id"],
                season_id=season.id,
                episode_number=row["episode_number"],
                title=row["episode_title"],
                description=row["synopsis"],
                duration=row["duration_seconds"],
                language=row["language"],
                content_group=row["content_group"],
                status=row["status"],
            )

            db.add(episode)
            db.flush()

            imported_episodes += 1

            # ---------------------------------------------------------
            # 6. Create seed artwork records
            # ---------------------------------------------------------
            for artwork_type in row.get("artwork_available", []):
                existing_artwork = (
                    db.query(Artwork)
                    .filter(
                        Artwork.episode_id == episode.id,
                        Artwork.artwork_type == artwork_type,
                    )
                    .first()
                )

                if existing_artwork is None:
                    artwork = Artwork(
                        episode_id=episode.id,
                        artwork_type=artwork_type,
                        file_path=(
                            f"seed/{row['episode_id']}/"
                            f"{artwork_type}"
                        ),
                        width=0,
                        height=0,
                        file_size=0,
                    )

                    db.add(artwork)

        db.commit()

        print()
        print("========================================")
        print("SEED IMPORT COMPLETE")
        print("========================================")
        print(f"New episodes imported : {imported_episodes}")
        print(f"Episodes skipped      : {skipped_episodes}")
        print(
            f"New duplicate issues  : "
            f"{duplicate_issues_added}"
        )
        print("========================================")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()